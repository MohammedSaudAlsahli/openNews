import SwiftUI
import AppKit

func settingsHeading(_ title: String, subtitle: String) -> some View {
    VStack(alignment: .leading, spacing: 6) {
        Text(title).font(.title2.weight(.semibold))
        Text(subtitle).font(.callout).foregroundStyle(.secondary)
    }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
}

func credentialLabel(_ field: String) -> String {
    ["api_key": L("مفتاح API"), "aws_access_key_id": L("معرّف مفتاح AWS"), "aws_secret_access_key": L("المفتاح السري AWS"), "aws_session_token": L("رمز جلسة AWS"), "azure_management_token": L("رمز إدارة Azure"), "portkey_api_key": L("مفتاح Portkey"), "virtual_key": L("المفتاح الافتراضي"), "auth_token": L("رمز المصادقة")][field] ?? field
}

func fieldLabel(_ field: String) -> String {
    ["base_url": L("عنوان الخدمة"), "host": L("عنوان الخادم"), "api_base": L("عنوان API"), "region": L("المنطقة"), "aws_region": L("منطقة AWS"), "project_id": L("معرّف المشروع"), "location": L("الموقع"), "subscription_id": L("معرّف الاشتراك"), "resource_group": L("مجموعة الموارد"), "account_name": L("اسم الحساب"), "timeout": L("مهلة الاتصال"), "organization": L("المؤسسة")][field] ?? field
}

// Isolate technical identifiers without changing the surrounding interface direction.
func technicalIdentifier(_ value: String) -> String {
    "\u{2066}" + value + "\u{2069}"
}
