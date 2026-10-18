use serde_json::Value;
use std::{
    io::Write,
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::Path,
};
/// Match the engine's owner-only credential store. Never return secrets to the UI.
pub fn save(workspace: &Path, profile: &str, values: Value) -> Result<(), String> {
    uuid::Uuid::parse_str(profile).map_err(|_| "Invalid connection")?;
    let object = values.as_object().ok_or("Invalid credentials")?;
    if object.is_empty() || object.values().any(|v| !v.is_string() && !v.is_object()) {
        return Err("Invalid credentials".into());
    }
    let bytes = serde_json::to_vec(&values).map_err(|_| "Invalid credentials")?;
    if bytes.len() > 65536 {
        return Err("Credentials too large".into());
    }
    let directory = workspace.join(".providers");
    if directory
        .symlink_metadata()
        .is_ok_and(|m| m.file_type().is_symlink())
    {
        return Err("Unsafe credential directory".into());
    }
    std::fs::create_dir_all(&directory).map_err(|_| "Cannot create credential directory")?;
    std::fs::set_permissions(&directory, std::fs::Permissions::from_mode(0o700))
        .map_err(|_| "Cannot protect credentials")?;
    // Hold the directory open, avoiding link substitution while creating/replacing.
    let handle = std::fs::OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW)
        .open(&directory)
        .map_err(|_| "Unsafe credential directory")?;
    use std::os::fd::AsRawFd;
    let temporary = std::ffi::CString::new(format!(".{}.tmp", uuid::Uuid::new_v4())).unwrap();
    let destination = std::ffi::CString::new(format!("{profile}.json")).unwrap();
    let fd = unsafe {
        libc::openat(
            handle.as_raw_fd(),
            temporary.as_ptr(),
            libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL | libc::O_NOFOLLOW,
            0o600,
        )
    };
    if fd < 0 {
        return Err("Cannot save credentials".into());
    }
    use std::os::fd::FromRawFd;
    let mut file = unsafe { std::fs::File::from_raw_fd(fd) };
    let result = (|| {
        file.write_all(&bytes)
            .map_err(|_| "Cannot save credentials")?;
        file.sync_all().map_err(|_| "Cannot save credentials")?;
        if unsafe {
            libc::renameat(
                handle.as_raw_fd(),
                temporary.as_ptr(),
                handle.as_raw_fd(),
                destination.as_ptr(),
            )
        } != 0
        {
            return Err("Cannot commit credentials");
        }
        handle.sync_all().map_err(|_| "Cannot commit credentials")?;
        Ok(())
    })();
    unsafe {
        libc::unlinkat(handle.as_raw_fd(), temporary.as_ptr(), 0);
    }
    result.map_err(String::from)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn credentials_are_private_and_reject_links() {
        let temp = tempfile::tempdir().unwrap();
        let id = uuid::Uuid::new_v4().to_string();
        save(temp.path(), &id, serde_json::json!({"api_key":"test-only"})).unwrap();
        let path = temp.path().join(".providers").join(format!("{id}.json"));
        assert_eq!(
            std::fs::metadata(path).unwrap().permissions().mode() & 0o777,
            0o600
        );
        assert!(save(temp.path(), "../escape", serde_json::json!({"api_key":"x"})).is_err());
        let other = tempfile::tempdir().unwrap();
        std::os::unix::fs::symlink(temp.path(), other.path().join(".providers")).unwrap();
        assert!(save(other.path(), &id, serde_json::json!({"api_key":"x"})).is_err());
    }
}
