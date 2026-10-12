import SwiftUI

struct AssistantPreferences: Decodable {
    let settings: [String: String]
    let inherited: [AssistantPreferenceLayer]
}
struct AssistantPreferenceLayer: Decodable {
    let scope, targetId: String
    let settings: [String: String]
}

struct AssistantCustomizationButton: View {
    @AppStorage("appLanguage") private var language = "ar"
    let scope: String
    var targetID = ""
    @State private var presented = false
    var body: some View {
        let _ = language
        Button { presented = true } label: { Label(L("تخصيص المساعد"), systemImage: "slider.horizontal.3") }
            .sheet(isPresented: $presented) {
                AssistantCustomizationEditor(scope: scope, targetID: targetID).editorialPresentation()
            }
    }
}

struct AssistantCustomizationEditor: View {
    @AppStorage("appLanguage") private var language = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    let scope: String
    let targetID: String
    @State private var values: [String: String] = [:]
    @State private var baseline: [String: String] = [:]
    @State private var inherited: [AssistantPreferenceLayer] = []
    @State private var selection = "role"
    @State private var loading = true
    @State private var saving = false
    @State private var loaded = false
    @State private var failure: String?
    @State private var discard = false
    @State private var reset = false
    private var dirty: Bool { values != baseline }
    private var fieldsValid: Bool { values.allSatisfy { key, value in value.count <= (["role", "style", "output"].contains(key) ? 3000 : 6000) } }
    private var count: Int { values.values.reduce(0) { $0 + $1.count } }
    private var target: [String: Any] { ["scope": scope, "target_id": targetID] }
    private var fields: [(key: String, title: String, hint: String)] { [
        ("role", L("الدور والتخصص"), L("مثال: محرر تقني يساعدني على شرح الأخبار بلغة بسيطة.")),
        ("instructions", L("تعليمات العمل"), L("مثال: اقترح زاويتين، ثم اسألني أيهما أفضّل قبل كتابة المسودة.")),
        ("style", L("أسلوب الكتابة"), L("مثال: لغة عربية واضحة، نبرة ودودة، وجمل قصيرة بلا مبالغة.")),
        ("knowledge", L("المصادر والمعرفة"), L("أضف خلفية عن مشروعك وجمهورك. إضافة رابط هنا لا تشغّل متابعته؛ أضفه من مكتبة المصادر.")),
        ("examples", L("أمثلة تعجبني"), L("ضع مثالًا من كتابتك يوضح النبرة أو البناء الذي تفضّله.")),
        ("output", L("شكل الإجابة"), L("مثال: ابدأ بخلاصة قصيرة، ثم نقاط واضحة وروابط المصادر.")),
        ("system_prompt", "System prompt", L("تعليمات عامة لهوية المساعد وسلوكه. حقل اختياري للمستخدم المتقدم.")),
        ("developer_prompt", "Developer prompt", L("تعليمات تنفيذ إضافية. حقل اختياري للمستخدم المتقدم."))
    ] }
    private var selected: (key: String, title: String, hint: String) { fields.first { $0.key == selection } ?? fields[0] }
    private var scopeTitle: String {
        if scope == "general" { return L("تعليمات عامة لكل المحادثات والوكلاء") }
        if scope == "agent" { return L("تعليمات هذا الوكيل") }
        return L("تعليمات هذه المحادثة فقط")
    }
    var body: some View {
        let _ = language
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 5) {
                    Text(L("تخصيص المساعد")).font(.title2.weight(.semibold))
                    Text(scopeTitle).font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
            }.padding(22)
            Divider()
            HStack(alignment: .top, spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(fields.prefix(6), id: \.key) { field in fieldButton(field.key, field.title) }
                        DisclosureGroup(L("خيارات متقدمة")) {
                            ForEach(fields.suffix(2), id: \.key) { field in fieldButton(field.key, field.title) }
                        }.padding(.top, 12)
                    }.padding(16)
                }.frame(width: 210)
                Divider()
                VStack(alignment: .leading, spacing: 14) {
                    Text(selected.title).font(.headline)
                    Text(selected.hint).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    TextEditor(text: Binding(get: { values[selection] ?? "" }, set: { values[selection] = $0 }))
                        .font(.system(size: 15)).padding(8).scrollContentBackground(.hidden)
                        .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 8))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(nsColor: .separatorColor)))
                        .accessibilityLabel(selected.title)
                    if selection.hasSuffix("_prompt") {
                        Text(L("يكيّف التطبيق هذه التعليمات مع قناة التعليمات التي يدعمها المزوّد؛ ليست كل النماذج تدعم System وDeveloper كدورين منفصلين."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Text(L("كل الأقسام اختيارية. طلبك تكتبه في المحادثة كالمعتاد. لا تمنح التعليمات أدوات أو صلاحيات جديدة."))
                        .font(.caption).foregroundStyle(.secondary)
                    if scope != "general" {
                        DisclosureGroup(L("التعليمات العامة الموروثة")) {
                            ScrollView {
                                let entries = fields.filter { !(inherited.first?.settings[$0.key] ?? "").isEmpty }
                                if entries.isEmpty { Text(L("لا توجد تعليمات عامة مخصصة.")).font(.caption) }
                                ForEach(entries, id: \.key) { field in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(field.title).font(.caption.bold())
                                        ProseText(text: inherited.first?.settings[field.key] ?? "", fontSize: 13, lineSpacing: 3)
                                    }
                                }
                            }.frame(maxHeight: 110)
                        }.font(.caption)
                        Text(L("تُضاف هذه التعليمات إلى العامة. في المحادثة تُضاف أيضًا تعليمات الوكيل المختار؛ والتخصيص الأقرب للمهمة يحدد الأسلوب عند التعارض."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }.padding(22).frame(maxWidth: .infinity)
            }.disabled(loading || saving)
            Divider()
            if !fieldsValid { Text(L("تجاوز هذا القسم الحد المسموح. اختصر النص للمتابعة.")).font(.caption).foregroundStyle(.red) }
            if let failure { Text(failure).foregroundStyle(.red).font(.callout).padding(.horizontal, 22) }
            HStack {
                Button(L("مسح التخصيص")) { reset = true }.disabled(loading || saving)
                Text(L("{0} / 16000 حرف", count)).font(.caption).foregroundStyle(count > 16000 ? .red : .secondary)
                Spacer()
                if loading || saving { ProgressView().controlSize(.small) }
                Button(L("إلغاء")) { close() }.keyboardShortcut(.cancelAction).disabled(saving)
                Button(L("حفظ")) { Task { await save() } }.buttonStyle(.borderedProminent)
                    .keyboardShortcut(.defaultAction).disabled(!loaded || loading || saving || count > 16000 || !fieldsValid)
            }.padding(18)
        }.frame(width: 800, height: 640)
            .interactiveDismissDisabled(dirty || saving)
            .task { await load() }
            .alert(L("تجاهل التغييرات؟"), isPresented: $discard) {
                Button(L("تجاهل التغييرات"), role: .destructive) { dismiss() }
                Button(L("إلغاء"), role: .cancel) {}
            }
            .alert(L("مسح التخصيص؟"), isPresented: $reset) {
                Button(L("مسح"), role: .destructive) { values = baseline.mapValues { _ in "" } }
                Button(L("إلغاء"), role: .cancel) {}
            } message: { Text(L("سيُمسح تخصيص هذا المستوى عند الحفظ. تبقى مستويات التخصيص الأخرى والمصادر محفوظة.")) }
    }
    private func fieldButton(_ key: String, _ title: String) -> some View {
        Button { selection = key } label: {
            HStack {
                Text(title)
                Spacer(minLength: 4)
                if !(values[key] ?? "").isEmpty { Image(systemName: "checkmark").font(.caption).accessibilityLabel(L("مخصص")) }
            }.padding(9).frame(maxWidth: .infinity, alignment: .leading)
                .background(selection == key ? Color.accentColor.opacity(0.15) : .clear, in: RoundedRectangle(cornerRadius: 7))
        }.buttonStyle(.plain).accessibilityAddTraits(selection == key ? [.isSelected] : [])
    }
    private func close() { if dirty { discard = true } else { dismiss() } }
    private func load() async {
        defer { loading = false }
        do {
            let result = try await model.decoded("assistant.get", target, as: AssistantPreferences.self)
            values = result.settings; baseline = values; inherited = result.inherited; loaded = true
        } catch { failure = error.localizedDescription }
    }
    private func save() async {
        saving = true; failure = nil
        defer { saving = false }
        do {
            _ = try await model.call("assistant.save", target.merging(["settings": values]) { _, new in new })
            baseline = values; dismiss()
        } catch { failure = error.localizedDescription }
    }
}
