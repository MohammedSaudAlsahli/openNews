import Foundation

@main struct KeychainSmoke {
    static func main() throws {
        let account = CommandLine.arguments[1]
        if CommandLine.arguments.count == 2 {
            try Keychain.delete(account: account)
        } else {
            try Keychain.save("synthetic-test-value-not-a-real-key", account: account,
                              interpreter: URL(fileURLWithPath: CommandLine.arguments[2]))
        }
    }
}
