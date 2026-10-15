import SwiftUI

struct ProviderConnectionStatus: Decodable {
    let state: String
    let checkedAt, lastSuccessAt: String?
}

struct ConnectionStatusView: View {
    @EnvironmentObject private var model: StudioModel
    let profile: ProviderProfile
    var detailed = false
    var checking = false
    private var state: String { model.health == nil ? "engine_offline" : (profile.connection?.state ?? "configured") }
    private var title: String {
        if checking { return L("جارٍ التحقق…") }
        switch state {
        case "connected": return L("متصل — تم التحقق")
        case "disconnected": return L("غير متصل — تم فصله")
        case "needs_login": return L("يلزم إعادة الربط")
        case "network_error": return L("تعذّر الوصول — مشكلة شبكة")
        case "service_error": return L("الخدمة غير متاحة مؤقتًا")
        case "restricted": return L("الوصول مقيّد")
        case "limited": return L("بلغ حد الاستخدام")
        case "engine_offline": return L("المحرك غير متاح")
        case "unverified": return L("يلزم تحديث التحقق")
        case "check_failed": return L("تعذّر التحقق")
        default: return L("محفوظ — لم يُختبر بعد")
        }
    }
    private var symbol: String {
        if checking { return "arrow.triangle.2.circlepath" }
        switch state {
        case "connected": return "checkmark.circle.fill"
        case "disconnected": return "minus.circle"
        case "needs_login": return "person.crop.circle.badge.exclamationmark"
        case "network_error", "engine_offline": return "wifi.exclamationmark"
        default: return "exclamationmark.circle"
        }
    }
    private var tint: Color {
        if checking { return .secondary }
        if state == "connected" { return .green }
        if ["configured", "disconnected", "unverified"].contains(state) { return .secondary }
        return .orange
    }
    private var explanation: String {
        switch state {
        case "connected": return L("نجح آخر تحقق. تُراجع جلسة ChatGPT تلقائيًا كل خمس دقائق أثناء تشغيل التطبيق.")
        case "disconnected": return L("تم فصل الاتصال على هذا الجهاز وإزالة بيانات الدخول. أعد الربط لاستخدامه مجددًا.")
        case "needs_login": return L("بيانات الدخول مفقودة أو لم تعد صالحة. أعد الربط لمتابعة الاستخدام.")
        case "network_error", "service_error": return L("بيانات الدخول محفوظة. تعذّر تأكيد الاتصال الآن؛ أعد التحقق عند عودة الخدمة أو الشبكة.")
        case "restricted": return L("راجع صلاحيات الحساب لدى المزوّد. هذا الخطأ لا يعني تسجيل الخروج.")
        case "limited": return L("انتظر تجدد حد الاستخدام أو راجع إعدادات حسابك. لم تُحذف بيانات الدخول.")
        case "engine_offline": return L("تعذّر الاتصال بمحرك التطبيق؛ لا يمكن تأكيد حالة المزوّد الآن.")
        case "unverified": return L("نجح الاتصال سابقًا، لكن التحقق قديم. تحقّق من حالته الحالية.")
        default: return L("حفظ البيانات أو عرض قائمة النماذج لا يؤكد صلاحية الحساب. اختبار النموذج يؤكد قدرته على الرد.")
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: symbol).foregroundStyle(tint).font(.callout.weight(.medium))
            if detailed {
                Text(explanation).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                if let stamp = profile.connection?.checkedAt { Text(L("آخر تحقق: {0}", date(stamp))).font(.caption).foregroundStyle(.secondary) }
                if state != "connected", let stamp = profile.connection?.lastSuccessAt { Text(L("آخر اتصال ناجح: {0}", date(stamp))).font(.caption).foregroundStyle(.secondary) }
            }
        }
        .accessibilityElement(children: .combine)
    }
    private func date(_ value: String) -> String { DisplayFormat.date(value) }
}

struct ConnectionStatusRow: View {
    @EnvironmentObject private var model: StudioModel
    let profile: ProviderProfile
    let open: () -> Void
    var body: some View {
        Button(action: open) {
            HStack(spacing: 14) {
                if let provider = model.catalog?.providers.first(where: { $0.id == profile.providerKey }) {
                    ProviderBrandView(provider: provider, size: 36)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text(profile.displayName).font(.headline)
                    ConnectionStatusView(profile: profile)
                }
                Spacer(minLength: 12)
                Image(systemName: "chevron.forward").font(.caption).foregroundStyle(.secondary)
            }.padding(.vertical, 18).contentShape(Rectangle())
        }.buttonStyle(.plain).help(L("إدارة الاتصال"))
    }
}
