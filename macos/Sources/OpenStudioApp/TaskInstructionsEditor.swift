import SwiftUI

struct TaskInstructionDocument: Decodable {
    let id, content, defaultContent: String
    let limit: Int
}

struct TaskInstructionsButton: View {
    let documentID: String
    @State private var presented = false
    var body: some View {
        Button(L("عرض التعليمات وتعديلها")) { presented = true }
            .sheet(isPresented: $presented) {
                TaskInstructionsEditor(initialID: documentID).editorialPresentation()
            }
    }
}

struct TaskInstructionsEditor: View {
    init(initialID: String) { _selection = State(initialValue: initialID) }
    @EnvironmentObject private var model: StudioModel
    @Environment(\.dismiss) private var dismiss
    @AppStorage("appLanguage") private var language = "ar"
    @State private var selection = "article-summary"
    @State private var skills: [WritingSkill] = []
    @State private var document: TaskInstructionDocument?
    @StateObject private var markdownEditor = MarkdownEditorController()
    @State private var preview = true
    @State private var text = ""
    @State private var busy = false
    @State private var failure: String?
    @State private var reset = false
    @State private var discard = false
    private var dirty: Bool { document != nil && text != document?.content }
    private var title: String {
        if selection == "article-summary" { return L("تعليمات التلخيص") }
        if selection == "daily-report" { return L("التقرير اليومي") }
        return skills.first { "skill:" + $0.id == selection }?.title(language) ?? selection
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(L("تعليمات النموذج")).font(.title2.bold())
            Text(L("هذه التعليمات المستخدمة فعليًا. عدّلها هنا؛ تُحفظ على جهازك وتُطبّق على النتائج الجديدة.")).foregroundStyle(.secondary)
            Picker(L("المهمة"), selection: $selection) {
                Text(L("تعليمات التلخيص")).tag("article-summary")
                Text(L("التقرير اليومي")).tag("daily-report")
                ForEach(skills) { skill in Text(skill.title(language)).tag("skill:" + skill.id) }
            }.disabled(busy || dirty)
            Text(title).font(.headline)
            if busy && document == nil { ProgressView() }
            MarkdownFormattingToolbar(controller: markdownEditor, preview: $preview,
                enabled: !busy && document != nil, viewLabel: L("تعليمات النموذج"))
            ZStack(alignment: .topLeading) {
                MarkdownEditor(text: $text, controller: markdownEditor,
                    documentID: selection, interfaceLanguage: language,
                    editable: !busy && document != nil && !preview, fontSize: 16, lineSpacing: 7)
                    .opacity(preview ? 0 : 1).allowsHitTesting(!preview).accessibilityHidden(preview)
                if preview {
                    ScrollView {
                        RichTextView(text: text, fontSize: 16, lineSpacing: 7)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .textSelection(.enabled).padding(16)
                    }
                    .accessibilityLabel(L("معاينة"))
                }
            }.frame(maxHeight: .infinity)
                .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            if let failure { Text(failure).foregroundStyle(.red) }
            Text("\(text.count) / \(document?.limit ?? 16000)").font(.caption).foregroundStyle(.secondary)
            HStack {
                Button(L("استعادة الافتراضي")) { reset = true }.disabled(busy || document == nil)
                Spacer()
                Button(L("إغلاق")) { if dirty { discard = true } else { dismiss() } }
                Button(L("حفظ")) { Task { await request("instructions.save") } }
                    .buttonStyle(.borderedProminent)
                    .disabled(busy || !dirty || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || text.count > (document?.limit ?? 16000))
            }
        }.padding(24).frame(width: 780, height: 650)
            .interactiveDismissDisabled(dirty)
            .task {
                if let catalog = try? await model.decoded("skills.catalog", as: WritingSkillCatalog.self) { skills = catalog.skills }
                await request("instructions.get")
            }
            .onChange(of: selection) { _, _ in
                document = nil; text = ""
                Task { await request("instructions.get") }
            }
            .confirmationDialog(L("استعادة الافتراضي؟"), isPresented: $reset) {
                Button(L("استعادة الافتراضي"), role: .destructive) { Task { await request("instructions.reset") } }
            }
            .confirmationDialog(L("تجاهل التعديلات؟"), isPresented: $discard) {
                Button(L("تجاهل التعديلات"), role: .destructive) { dismiss() }
            }
    }
    private func request(_ command: String) async {
        busy = true; failure = nil
        let requestedID = selection
        defer { busy = false }
        do {
            let value = try await model.decoded(command, ["id": requestedID, "content": text], as: TaskInstructionDocument.self)
            guard selection == requestedID else { return }
            document = value; text = value.content
        } catch { failure = error.localizedDescription }
    }
}
