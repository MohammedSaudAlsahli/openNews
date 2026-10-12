import SwiftUI
import AppKit

extension Notification.Name {
    static let newEditorialDraft = Self("eis.newDraft")
    static let openEditorialDrafts = Self("eis.openDrafts")
    static let saveEditorialDraft = Self("eis.saveDraft")
    static let importEditorialSource = Self("eis.importSource")
    static let toggleEditorialReferences = Self("eis.toggleReferences")
    static let exportEditorialDraft = Self("eis.exportDraft")
    static let helpEditorialWriting = Self("eis.helpWriting")
}

struct ContentView: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @State private var draft: Draft?
    @State private var title = ""
    @State private var text = ""
    @State private var savedText = ""
    @State private var detail: DraftDetail?
    @StateObject private var markdownEditor = MarkdownEditorController()
    @State private var previewDraft = false
    @State private var showReferences = true
    @AppStorage("sideBySideWorkspace") private var sideBySideWorkspace = false
    @State private var referenceSection: ReferenceSection = .news
    @StateObject private var chat = ChatSession()
    @State private var selectedArticleIDs = Set<String>()
    @State private var compactPane = "conversation"
    @State private var selectedSourceID: String?
    @State private var importing = false
    @State private var generating = false
    @State private var showReview = false
    @State private var showJobs = false
    @State private var showDrafts = false
    @State private var draftQuery = ""
    @State private var confirmChange = false
    @State private var pendingDraft: Draft?
    @State private var pendingGenerationJobID: String?
    @State private var generatedDraftReady: Draft?
    @FocusState private var focused: EditorField?
    enum EditorField { case title, text }
    private var dirty: Bool { draft == nil ? !title.isEmpty || !text.isEmpty : text != savedText }
    private var canSave: Bool { !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && text.count <= 60000 && model.health != nil && !model.busy }
    private var activeJobs: [Job] { (model.snapshot?.jobs ?? []).filter(\.active) }
    private var draftList: [Draft] { (model.snapshot?.drafts ?? []).filter { draftQuery.isEmpty || $0.topic.localizedCaseInsensitiveContains(draftQuery) } }

    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            if model.health == nil {
                HStack {
                    if model.connecting { ProgressView().controlSize(.small) }
                    Text(model.connecting ? L("جارٍ فتح مساحة العمل…") : L("تعذّر الاتصال بمساحة العمل"))
                    Spacer()
                    if !model.connecting { Button(L("إعادة المحاولة")) { Task { await model.start() } } }
                }.font(.callout).padding(12).background(Color(nsColor: .controlBackgroundColor))
            }
            GeometryReader { geometry in
                let paired = sideBySideWorkspace && geometry.size.width >= (showReferences ? 1180 : 860)
                HStack(spacing: 0) {
                    if paired {
                        conversationArea.frame(width: max(420, min(620, geometry.size.width * 0.46)))
                        Divider()
                        writingArea.frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else {
                        VStack(spacing: 0) {
                            Picker(L("مساحة العمل"), selection: $compactPane) {
                                Text(L("المحادثة")).tag("conversation")
                                Text(L("المسودة")).tag("draft")
                            }.pickerStyle(.segmented).frame(maxWidth: 300).padding(12)
                            Divider()
                            if compactPane == "conversation" { conversationArea }
                            else { writingArea }
                        }.frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                    if showReferences {
                        Divider()
                        SourcePanel(section: $referenceSection, selectedSourceID: $selectedSourceID, selectedArticleIDs: $selectedArticleIDs) { importing = true }
                            .frame(width: 320).background(Color(nsColor: .windowBackgroundColor))
                    }
                }
            }
            Divider()
            statusBar
        }
        .background(Color(nsColor: .textBackgroundColor))
        .navigationTitle(L("مساحة التحرير"))
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button { sideBySideWorkspace.toggle() } label: { Label(L("عرض المحادثة والمسودة معًا"), systemImage: "rectangle.split.2x1") }
                    .help(L("عرض المحادثة والمسودة معًا"))
                Button { requestOpen(nil) } label: { Label(L("مسودة جديدة"), systemImage: "square.and.pencil") }.help(L("مسودة جديدة (⌘N)"))
                Button { showDrafts.toggle() } label: { Label(L("المسودات"), systemImage: "doc.on.doc") }
                    .popover(isPresented: $showDrafts, arrowEdge: .bottom) { draftsPopover }
                Divider()
                Button { Task { _ = await save() } } label: { Label(L("حفظ"), systemImage: "square.and.arrow.down") }
                    .disabled(!canSave || !dirty).help(L("حفظ نسخة (⌘S)"))
                Button { Task { await export() } } label: { Label(L("تصدير"), systemImage: "square.and.arrow.up") }
                    .disabled(!canSave).help(L("تصدير Markdown للمراجعة"))
                Divider()
                Button { showReferences.toggle() } label: { Label(L("الأخبار والكتابات"), systemImage: "sidebar.trailing") }
                    .help(showReferences ? L("إخفاء الأخبار والكتابات") : L("إظهار الأخبار والكتابات"))
            }
        }
        .sheet(isPresented: $importing) {
            ImportSourceSheet { id in selectedSourceID = id; referenceSection = .sources; showReferences = true }
        }
        .sheet(isPresented: $generating) {
            GenerationSheet(onSubmitted: { jobID in
                pendingGenerationJobID = jobID
            }, onShowSources: { referenceSection = .sources; showReferences = true })
        }
        .confirmationDialog(L("لديك تعديلات غير محفوظة"), isPresented: $confirmChange, titleVisibility: .visible) {
            Button(L("حفظ ثم المتابعة")) { let target = pendingDraft; Task { if await save() { await load(target) } } }.disabled(!canSave)
            Button(L("تجاهل التعديلات"), role: .destructive) { let target = pendingDraft; Task { await load(target) } }
            Button(L("إلغاء"), role: .cancel) { pendingDraft = nil }
        } message: { Text(L("احفظ كتابتك قبل الانتقال إلى مسودة أخرى.")) }
        .alert(L("تعذّر إكمال العملية"), isPresented: Binding(get: { model.error != nil && !importing && !generating }, set: { if !$0 { model.error = nil } })) {
            Button(L("حسنًا"), role: .cancel) { model.error = nil }
        } message: { Text(L(model.error ?? "")) }
        .background(BackgroundWindowHost())
        .onChange(of: dirty) { _, value in model.hasUnsavedChanges = value }
        .onChange(of: model.snapshot?.jobs.map { $0.id + $0.state } ?? []) { _, _ in
            Task { await receiveGeneratedDraft(); await chat.update(model) }
        }
        .onReceive(NotificationCenter.default.publisher(for: .openEditorialDrafts)) { _ in showDrafts = true }
        .onReceive(NotificationCenter.default.publisher(for: .newEditorialDraft)) { _ in if !model.busy { requestOpen(nil) } }
        .onReceive(NotificationCenter.default.publisher(for: .saveEditorialDraft)) { _ in if canSave && dirty { Task { _ = await save() } } }
        .onReceive(NotificationCenter.default.publisher(for: .importEditorialSource)) { _ in importing = true }
        .onReceive(NotificationCenter.default.publisher(for: .toggleEditorialReferences)) { _ in showReferences.toggle() }
        .onReceive(NotificationCenter.default.publisher(for: .exportEditorialDraft)) { _ in if canSave { Task { await export() } } }
        .onReceive(NotificationCenter.default.publisher(for: .helpEditorialWriting)) { _ in compactPane = "conversation"; chat.includeDraft = !text.isEmpty }
    }

    private var conversationArea: some View {
        ConversationPanel(session: chat, selectedArticleIDs: $selectedArticleIDs, draftText: text, draftTitle: title, openDraft: { id in
            Task {
                do {
                    try await model.refresh()
                    if let item = model.snapshot?.drafts.first(where: { $0.id == id }) { requestOpen(item) }
                    else { model.error = L("تعذّر العثور على المسودة. حدّث مساحة العمل ثم حاول مجددًا.") }
                } catch { model.error = error.localizedDescription }
            }
        }, showNews: { referenceSection = .news; showReferences = true })
    }

    private var writingArea: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .center) {
                Text(draft == nil ? L("مسودة جديدة") : L("مسودة للمراجعة")).font(.callout).foregroundStyle(.secondary)
                Spacer()
                if draft != nil {
                    Button { showReview.toggle() } label: { Label(L("المراجعة والنسخ"), systemImage: "checklist") }
                        .buttonStyle(.borderless)
                }
            }.padding(.bottom, 20)
            if draft == nil {
                TextField("", text: $title).textFieldStyle(.plain)
                    .font(.system(size: 24, weight: .semibold)).multilineTextAlignment(.leading).focused($focused, equals: .title)
                    .overlay(alignment: .leading) {
                        if title.isEmpty {
                            Text(L("عنوان المسودة")).font(.system(size: 24, weight: .semibold))
                                .foregroundStyle(.secondary).allowsHitTesting(false).accessibilityHidden(true)
                        }
                    }
                    .accessibilityLabel(L("عنوان المسودة الجديدة")).disabled(model.busy)
            } else {
                Text(title).font(.system(size: 24, weight: .semibold)).lineLimit(3).textSelection(.enabled)
            }
            Divider().padding(.top, 18).padding(.bottom, 8)
            MarkdownFormattingToolbar(controller: markdownEditor, preview: $previewDraft, enabled: !model.busy)
                .padding(.bottom, 12)
            ZStack(alignment: .topLeading) {
                if text.isEmpty {
                    Text(previewDraft ? L("ستظهر معاينة النص هنا بعد الكتابة.") : L("ابدأ الكتابة هنا…\nحدّد نصًا واستخدم أدوات التنسيق أعلاه."))
                        .font(.system(size: 18)).foregroundStyle(.secondary).lineSpacing(8).padding(5)
                        .allowsHitTesting(false).accessibilityHidden(true)
                }
                MarkdownEditor(text: $text, controller: markdownEditor,
                    documentID: draft?.id ?? "new", interfaceLanguage: interfaceLanguage, editable: !model.busy && !previewDraft)
                    .opacity(previewDraft ? 0 : 1).allowsHitTesting(!previewDraft).accessibilityHidden(previewDraft)
                    .focused($focused, equals: .text)
                if previewDraft && !text.isEmpty {
                    ScrollView {
                        ReadingColumn { RichTextView(text: text, fontSize: 18, lineSpacing: 8) }.padding(.vertical, 5)
                    }
                }
            }.frame(maxHeight: .infinity)
            if text.count > 60000 { Text(L("تجاوز النص حد الحفظ: {0} حرف.", 60000)).font(.caption).foregroundStyle(.red) }
            if showReview, let detail {
                Divider().padding(.vertical, 12)
                DraftReview(detail: detail).frame(maxHeight: 220)
            }
            HStack {
                Button { compactPane = "conversation"; chat.includeDraft = !text.isEmpty } label: { Label(L("ناقش هذه المسودة"), systemImage: "bubble.left.and.bubble.right") }
                    .buttonStyle(.bordered).disabled(model.health == nil || model.busy)
                Spacer()
                Text(draft == nil ? L("الكتابة والحفظ على جهازك") : L("الحفظ ينشئ نسخة جديدة"))
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(.top, 22)
        }.padding(32)
    }

    private var statusBar: some View {
        HStack(spacing: 14) {
            if model.busy { ProgressView().controlSize(.mini) }
            Label(dirty ? L("تعديلات غير محفوظة") : (draft == nil ? L("جاهز للكتابة") : L("محفوظ على جهازك")), systemImage: dirty ? "pencil.tip" : "checkmark.circle")
            Text(L("{0} كلمة · {1} حرف", text.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count, text.count))
                .foregroundStyle(.secondary).monospacedDigit()
            Spacer()
            if let ready = generatedDraftReady {
                Button(L("المسودة الجديدة جاهزة — فتح")) { requestOpen(ready) }.disabled(model.busy)
            }
            if let notice = model.notice {
                Text(L(notice)).lineLimit(1).help(notice)
                Button { model.notice = nil } label: { Image(systemName: "xmark") }.buttonStyle(.plain).accessibilityLabel(L("إغلاق الإشعار"))
            }
            Button { showJobs.toggle() } label: {
                Label(activeJobs.isEmpty ? L("النشاط") : L("جارٍ العمل ({0})", activeJobs.count), systemImage: activeJobs.isEmpty ? "clock" : "arrow.triangle.2.circlepath")
            }.buttonStyle(.borderless)
                .popover(isPresented: $showJobs) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(L("النشاط")).font(.headline)
                        if model.snapshot?.jobs.isEmpty != false { Text(L("ستظهر هنا عمليات التحليل والتوليد.")).foregroundStyle(.secondary) }
                        ScrollView { VStack(spacing: 12) { ForEach(model.snapshot?.jobs ?? []) { job in ActivityRow(job: job) } } }.frame(maxHeight: 360)
                    }.padding(20).frame(width: 360).editorialPresentation()
                }
        }.font(.caption).padding(.horizontal, 18).frame(height: 36).background(Color(nsColor: .windowBackgroundColor))
    }

    private var draftsPopover: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(L("المسودات المحفوظة")).font(.headline)
            TextField(L("ابحث بالعنوان"), text: $draftQuery).textFieldStyle(.roundedBorder).accessibilityLabel(L("البحث في المسودات"))
            if draftList.isEmpty { Text(draftQuery.isEmpty ? L("احفظ أول مسودة لتجدها هنا.") : L("لا توجد مسودة بهذا العنوان.")).foregroundStyle(.secondary).padding(.vertical, 16) }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(draftList) { item in
                        Button { showDrafts = false; requestOpen(item) } label: {
                            HStack(alignment: .top, spacing: 10) {
                                Image(systemName: item.id == draft?.id ? "doc.text.fill" : "doc.text").foregroundStyle(.secondary)
                                VStack(alignment: .leading, spacing: 5) {
                                    Text(item.topic).fontWeight(.medium).lineLimit(2)
                                    Text(item.text).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                                }
                                Spacer(minLength: 0)
                            }.frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle()).padding(.vertical, 10)
                        }.buttonStyle(.plain)
                        Divider()
                    }
                }
            }.frame(maxHeight: 350)
        }.padding(20).frame(width: 330).editorialPresentation()
    }

    private func receiveGeneratedDraft() async {
        guard let id = pendingGenerationJobID, let job = model.snapshot?.jobs.first(where: { $0.id == id }), !job.active else { return }
        pendingGenerationJobID = nil
        guard job.state == "completed" else { model.notice = L("تعذّر إعداد المسودة. افتح النشاط للتفاصيل والمحاولة مجددًا."); return }
        do {
            let result = try await model.decoded("jobs.get", ["job_id": id], as: JobDetail.self)
            guard let json = result.resultJson?.data(using: .utf8) else { return }
            let generated = try JSONDecoder.engine.decode(GeneratedResult.self, from: json)
            guard let item = model.snapshot?.drafts.first(where: { $0.id == generated.draftId }) else { return }
            if !dirty && !model.busy { await load(item) }
            else { generatedDraftReady = item }
        } catch { model.error = error.localizedDescription }
    }

    private func requestOpen(_ next: Draft?) {
        guard !model.busy else { return }
        if next?.id == draft?.id && next != nil { return }
        if dirty { pendingDraft = next; confirmChange = true }
        else { Task { await load(next) } }
    }

    private func load(_ next: Draft?) async {
        model.busy = true
        defer { model.busy = false }
        do {
            var loaded: DraftDetail?
            if let next { loaded = try await model.decoded("drafts.detail", ["draft_id": next.id], as: DraftDetail.self) }
            if generatedDraftReady?.id == next?.id { generatedDraftReady = nil }
            draft = next; detail = loaded; title = next?.topic ?? ""; compactPane = "draft"
            text = loaded?.versions.first(where: { $0.id == next?.currentVersionId })?.text ?? loaded?.versions.first?.text ?? ""
            savedText = text; showReview = false; pendingDraft = nil; previewDraft = false
            model.hasUnsavedChanges = false; model.notice = nil
            focused = next == nil ? .title : .text
        } catch { model.error = error.localizedDescription }
    }

    @discardableResult private func save() async -> Bool {
        guard canSave else { return false }
        let submittedText = text
        model.busy = true
        defer { model.busy = false }
        do {
            let id: String
            if let draft {
                _ = try await model.call("drafts.save", ["draft_id": draft.id, "text": submittedText]); id = draft.id
            } else {
                let name = title.trimmingCharacters(in: .whitespacesAndNewlines)
                let created = try await model.decoded("drafts.create", ["topic": name.isEmpty ? String(submittedText.prefix(60)) : name, "text": submittedText], as: CreatedDraft.self)
                id = created.draftId
            }
            try await model.refresh()
            draft = model.snapshot?.drafts.first { $0.id == id }
            title = draft?.topic ?? title
            detail = try await model.decoded("drafts.detail", ["draft_id": id], as: DraftDetail.self)
            savedText = submittedText; model.hasUnsavedChanges = dirty
            model.notice = L("حُفظت نسخة جديدة"); return true
        } catch { model.error = error.localizedDescription; return false }
    }

    private func export() async {
        if dirty || draft == nil { guard await save() else { return } }
        if let draft { await model.export(draft) }
    }
}

struct DraftReview: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    let detail: DraftDetail
    var body: some View {
        let _ = interfaceLanguage
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(L("المراجعة والنسخ")).font(.headline)
                Text(L("هذه مسودة غير معتمدة. راجع الوقائع والأصالة قبل النشر.")).font(.callout).foregroundStyle(.secondary)
                if let latest = detail.versions.first, let data = latest.warningsJson.data(using: .utf8), let warnings = try? JSONDecoder().decode([String].self, from: data) {
                    ForEach(warnings, id: \.self) { Label(L($0), systemImage: "exclamationmark.circle").font(.callout) }
                }
                ForEach(detail.claims) { claim in
                    DisclosureGroup {
                        Text(claim.rationale).font(.callout)
                        ForEach(claim.evidence) { Text($0.text).font(.callout).textSelection(.enabled) }
                    } label: { VStack(alignment: .leading, spacing: 4) {
                        Label(claim.text, systemImage: "questionmark.circle")
                        Text(claim.verdict == "opinion" ? L("رأي") : L("يحتاج مراجعة")).foregroundStyle(.secondary).font(.caption)
                    }.font(.callout) }
                }
                if let evidence = detail.newsEvidence, !evidence.isEmpty {
                    DisclosureGroup(L("مراجع الأخبار ({0})", evidence.count)) {
                        ForEach(evidence) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                if let url = URL(string: item.url), ["https", "http"].contains(url.scheme?.lowercased() ?? "") { Link(item.title, destination: url) }
                                if let date = item.publishedAt { Text(DisplayFormat.date(date)).font(.caption).foregroundStyle(.secondary) }
                                if !item.excerpt.isEmpty { Text(item.excerpt).font(.callout).textSelection(.enabled) }
                            }
                        }
                        Text(L("هذه مراجع مستخدمة في المسودة؛ راجع الوقائع قبل النشر.")).font(.caption).foregroundStyle(.secondary)
                    }
                }
                if detail.versions.count > 1 {
                    DisclosureGroup(L("النسخ السابقة ({0})", detail.versions.count - 1)) {
                        ForEach(detail.versions.dropFirst()) { version in
                            DisclosureGroup(DisplayFormat.date(version.createdAt)) { RichTextView(text: version.text, fontSize: 14) }
                        }
                    }.font(.callout)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct ActivityRow: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject var model: StudioModel
    let job: Job
    @State private var resume = false
    private var state: String { ["queued": L("في الانتظار"), "running": L("جارٍ التنفيذ"), "completed": L("اكتملت"), "failed": L("تعذّرت"), "interrupted": L("توقفت"), "cancelled": L("أُلغيت")][job.state] ?? L("تحتاج مراجعة") }
    var body: some View {
        let _ = interfaceLanguage
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                if job.active { ProgressView().controlSize(.small) }
                Text(job.type == "analysis.run" ? L("تحليل المصدر") : (job.type == "chat.send" ? L("رد المحادثة") : L("كتابة مسودة"))).fontWeight(.medium)
                Spacer(); Text(state).foregroundStyle(.secondary)
            }
            if let code = job.errorCode {
                Text(L("تعذّرت العملية. راجع الإعدادات والموافقة قبل إعادة المحاولة.")).font(.caption)
                DisclosureGroup(L("تفاصيل المشكلة")) { Text(code).font(.caption.monospaced()).textSelection(.enabled) }
            }
            if job.active { Button(L("إلغاء العملية")) { Task { await model.perform("jobs.cancel", ["job_id": job.id]) } } }
            if ["failed", "interrupted", "cancelled"].contains(job.state) { Button(L("إعادة المحاولة…")) { resume = true } }
            Divider()
        }.font(.callout).confirmationDialog(L("قد تعيد المحاولة إرسال البيانات إلى النموذج وتكرار التكلفة."), isPresented: $resume, titleVisibility: .visible) {
            Button(L("أوافق، أعد المحاولة")) { Task { await model.perform("jobs.resume", ["job_id": job.id, "consent": true]) } }
            Button(L("إلغاء"), role: .cancel) { }
        }
    }
}

struct BackgroundWindowHost: NSViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSView { NSView() }
    func updateNSView(_ view: NSView, context: Context) {
        DispatchQueue.main.async {
            if let window = view.window {
                window.identifier = NSUserInterfaceItemIdentifier("editorial-studio")
                window.delegate = context.coordinator
            }
        }
    }
    final class Coordinator: NSObject, NSWindowDelegate {
        func windowShouldClose(_ sender: NSWindow) -> Bool {
            // Keep editor/chat state alive. Explicit Quit still checks unsaved edits.
            sender.orderOut(nil)
            return false
        }
    }
}
