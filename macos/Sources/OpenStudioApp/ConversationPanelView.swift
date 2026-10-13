import SwiftUI
import AppKit

struct ConversationPanel: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject private var model: StudioModel
    @Environment(\.openSettings) private var openSettings
    @ObservedObject var session: ChatSession
    @Binding var selectedArticleIDs: Set<String>
    let draftText: String
    let draftTitle: String
    let openDraft: (String) -> Void
    let showNews: () -> Void
    @AppStorage(ModelPermission.key) private var modelPermission = false
    @State private var modelOptions = false
    @State private var contextOptions = false
    @State private var customization = false
    @State private var attachArticle = false
    @State private var articleURL = ""
    @State private var attaching = false
    @State private var attachmentError: String?
    @State private var attachedArticle: ImportedArticle?
    @FocusState private var composerFocused: Bool
    private var canSend: Bool {
        !session.composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && session.composer.count <= 12000 &&
        (session.includeDraft ? draftText.count <= 60000 : true) && session.modelReady && modelPermission && !session.sending && model.health != nil
    }
    private var writerAssignmentRevision: String {
        guard let item = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) else { return "" }
        return item.profileId + "|" + item.modelId
    }
    private var jobRevision: [String] {
        let jobs: [Job] = model.snapshot?.jobs ?? []
        return jobs.map { $0.id + $0.state }
    }

    var body: some View {
        let _ = interfaceLanguage
        configuredConversation
                        .onChange(of: writerAssignmentRevision) { _, _ in
                if session.agentID.isEmpty, !session.sending,
                   let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    session.profileID = assignment.profileId; session.modelID = assignment.modelId
                }
            }
    }

    private var configuredConversation: some View {
        conversationLayout
            .task(id: model.snapshot?.workspaceId) { await session.start(model) }
            .task(id: session.jobID) { if let id = session.jobID { await session.monitor(model, job: id) } }
            .sheet(isPresented: $customization) {
                AssistantCustomizationEditor(scope: "conversation", targetID: session.conversationID).editorialPresentation()
            }
            .sheet(isPresented: $attachArticle) { articleAttachmentSheet.editorialPresentation() }
            .task(id: session.profileID + "|" + session.modelID) { await validateModelSelection() }
            .onChange(of: agentRevision) { _, _ in updateAgentConfiguration() }
            .onChange(of: jobRevision) { _, _ in Task { await session.update(model) } }
            .onChange(of: session.format) { _, value in
                if value == "youtube_long" { session.seconds = 600 }
                else if value == "tiktok" { session.seconds = 60 }
            }
    }

    private var isWelcome: Bool { session.detail?.messages.isEmpty != false && !session.sending }
    private var conversationLayout: some View {
        VStack(spacing: 0) {
            conversationHeader
            Divider()
            if isWelcome {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(L("بماذا نبدأ؟")).font(.system(size: 30, weight: .semibold))
                            Text(L("ناقش فكرة أو حوّل أخبار مصادرِك إلى محتوى بأسلوبك."))
                                .font(.title3).foregroundStyle(.secondary)
                        }
                        composer
                        startingPrompts
                        if session.error != nil { failureNotice }
                    }.frame(maxWidth: 720, alignment: .leading).padding(32)
                        .padding(.top, 70).frame(maxWidth: .infinity)
                }
            } else {
                messageHistory
                composer.frame(maxWidth: 800).padding(20).frame(maxWidth: .infinity)
            }
        }.background(Color(nsColor: .textBackgroundColor))
    }
    private var conversationHeader: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text(session.detail?.title ?? L("محادثة جديدة")).font(.headline).lineLimit(1)
                Text(L(session.loading ? "جارٍ تحميل المحادثة…" : session.sending ? "جارٍ إعداد الرد…" : session.error != nil ? "تحتاج المحادثة انتباهك" : session.conversationID.isEmpty ? "لم تبدأ المحادثة بعد" : "محفوظة على جهازك"))
                    .font(.caption).foregroundStyle(.secondary)
                if let digest = model.digestStatus, digest.enabled, !digest.currentTitle.isEmpty {
                    Label(L("يلخّص الآن: {0}", digest.currentTitle), systemImage: "sparkles")
                        .font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                }
            }
            Spacer()
            Button {
                Task {
                    guard !session.loading else { return }
                    session.loading = true
                    defer { session.loading = false }
                    do {
                        if session.conversationID.isEmpty {
                            let created = try await model.decoded("chat.create", ["title": L("محادثة جديدة")], as: CreatedConversation.self)
                            session.conversationID = created.conversationId
                            await session.refreshList(model)
                        }
                        customization = true
                    } catch { session.error = error.localizedDescription }
                }
            } label: { Label(L("تخصيص المساعد"), systemImage: "slider.horizontal.3") }
                .buttonStyle(.borderless).disabled(session.sending || session.loading || model.health == nil)
            if session.loading { ProgressView().controlSize(.small) }
        }.padding(.horizontal, 24).padding(.vertical, 16)
    }
    private var failureNotice: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(session.error ?? "", systemImage: "exclamationmark.circle").foregroundStyle(.red).textSelection(.enabled)
            HStack {
                if let last = session.detail?.lastJob, ["failed", "interrupted", "cancelled"].contains(last.state) {
                    Button(L("إعادة المحاولة")) { Task { await session.retry(model) } }.disabled(!modelPermission || session.sending)
                }
                Button(L("إعدادات الاتصال")) { UserDefaults.standard.set("connections", forKey: "settingsSection"); openSettings() }
                Button(L("إغلاق التنبيه")) { session.error = nil }
            }.font(.caption)
            if let code = session.detail?.lastJob?.errorCode {
                DisclosureGroup(L("تفاصيل المشكلة")) { Text(code).font(.caption.monospaced()).textSelection(.enabled) }
            }
        }.font(.callout).padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
    }

    private var messageHistory: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 22) {
                    if session.detail?.hasMore == true {
                        HStack {
                            Button(L("تحميل رسائل أقدم")) { Task { await session.loadOlder(model) } }.disabled(session.loadingOlder)
                            if session.loadingOlder { ProgressView().controlSize(.small) }
                        }.font(.caption)
                    }
                    ForEach(session.detail?.messages ?? []) { message in
                        messageView(message).id(message.id)
                    }
                    if session.sending {
                        VStack(alignment: .leading, spacing: 14) {
                            HStack(spacing: 8) {
                                ProgressView().controlSize(.small)
                                Text(progressTitle).font(.callout)
                                if let progress = session.progress { Text(L("{0} ثانية", progress.elapsedSeconds)).font(.caption).monospacedDigit().foregroundStyle(.secondary) }
                            }
                            if let progress = session.progress {
                                ConversationActivity(progress: progress, model: model)
                            }
                            if let progress = session.progress, !progress.message.isEmpty {
                                RichTextView(text: ConversationPresentation.markdown(progress.message, citations: progress.citations, partial: true), fontSize: 16, lineSpacing: 7, citationPreview: preview(for: progress.citations))
                                Text(L("رد جارٍ؛ يُحفظ بعد اكتماله والتحقق من تنسيقه ومراجعه.")).font(.caption).foregroundStyle(.secondary)
                            }
                        }.id("pending")
                    }
                    if session.error != nil { failureNotice }
                }.frame(maxWidth: 720, alignment: .leading).padding(24).frame(maxWidth: .infinity)
            }
            .onChange(of: session.detail?.messages.last?.id) { _, _ in
                if let last = session.detail?.messages.last?.id { proxy.scrollTo(last, anchor: .bottom) }
            }
        }
    }
    private func preview(for citations: [ConversationCitation]) -> (URL) -> AnyView? {
        { url in
            guard let citation = citations.first(where: { URL(string: $0.url) == url }) else { return nil }
            return AnyView(CitationPreview(citation: citation, model: model))
        }
    }
    private var progressTitle: String {
        switch session.progress?.stage {
        case "researching": return L("يبحث عن أخبار حديثة ويقرأ المقالات…")
        case "waiting_model", "queued": return L("بانتظار النموذج…")
        case "validating": return L("جارٍ مراجعة التنسيق والمراجع…")
        default: return L(session.progress?.message.isEmpty == false ? "جارٍ كتابة الرد…" : "النموذج يجهّز الرد…")
        }
    }
    private var startingPrompts: some View {
        VStack(alignment: .leading, spacing: 14) {
            Button(L("ناقش معي أخبار هذا الأسبوع")) { session.composer = L("لخّص أهم أخبار هذا الأسبوع من اشتراكاتي، ثم اقترح ثلاث زوايا تستحق النقاش."); session.format = "discussion" }
                .buttonStyle(.link)
            Button(L("حوّل فكرة إلى منشورات X")) { session.composer = L("ساعدني على اختيار زاوية واضحة، ثم اكتب عدة منشورات X مستقلة بأسلوبي."); session.format = "x_posts" }
                .buttonStyle(.link)
            Button(L("إضافة مصادر للأخبار…"), action: showNews).buttonStyle(.link)
        }.padding(.vertical, 8)
    }
    @ViewBuilder private func messageView(_ message: ConversationMessage) -> some View {
        if message.role == "user" {
            HStack {
                Spacer(minLength: 70)
                Text(verbatim: message.content).font(.system(size: 16)).lineSpacing(6).textSelection(.enabled)
                    .multilineTextAlignment(.leading).fixedSize(horizontal: false, vertical: true)
                    .environment(\.layoutDirection, RichTextDirection.detect(message.content))
                    .padding(16).background(Color.primary.opacity(0.07), in: RoundedRectangle(cornerRadius: 16))
                    .frame(maxWidth: 580, alignment: .trailing).accessibilityLabel(L("أنت") + ": " + message.content)
            }.environment(\.layoutDirection, .leftToRight).padding(.bottom, 8)
        } else {
            VStack(alignment: .leading, spacing: 16) {
                Label(L("المساعد التحريري"), systemImage: "sparkles").font(.caption).foregroundStyle(.secondary)
                RichTextView(text: ConversationPresentation.markdown(message.content, citations: message.citations ?? []), fontSize: 16, lineSpacing: 7, citationPreview: preview(for: message.citations ?? []))
                ForEach(message.outputs ?? []) { output in
                    ConversationDraftCard(output: output, openDraft: openDraft).disabled(model.busy)
                }
                if let citations = message.citations, !citations.isEmpty {
                    CitationSources(citations: citations)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
    private func validateModelSelection() async {
        let profile = session.profileID, selected = session.modelID
        session.modelReady = false
        guard !profile.isEmpty, !selected.isEmpty else { return }
        do {
            let result = try await model.decoded("providers.models", ["profile_id": profile, "refresh": false], as: ProviderModels.self)
            guard !Task.isCancelled, session.profileID == profile, session.modelID == selected else { return }
            session.modelReady = result.models.contains { $0.id == selected && $0.available }
        } catch {
            guard !Task.isCancelled, session.profileID == profile else { return }
            session.error = error.localizedDescription
        }
    }
    private var agentRevision: [String] { model.customAgents.map { $0.id + $0.updatedAt } }
    private func updateAgentConfiguration() {
        guard !session.agentID.isEmpty else { return }
        if let agent = model.customAgents.first(where: { $0.id == session.agentID }) {
            session.profileID = agent.profileId; session.modelID = agent.modelId
        } else { session.agentID = ""; session.modelReady = false }
    }
    private var agentPicker: some View {
            NativeChoicePicker(title: L("الوكيل"), selection: $session.agentID,
                              choices: [PickerChoice(value: "", label: L("الكاتب الافتراضي"))]
                              + model.customAgents.map { PickerChoice(value: $0.id, label: $0.name) })
            .fixedSize().disabled(session.sending)
            .onChange(of: session.agentID) { _, selected in
                session.modelReady = false
                if let agent = model.customAgents.first(where: { $0.id == selected }) {
                    session.profileID = agent.profileId; session.modelID = agent.modelId
                } else if let assignment = model.snapshot?.assignments?.first(where: { $0.role == "writer" }) {
                    session.profileID = assignment.profileId; session.modelID = assignment.modelId
                }
            }
    }
    private var outputPicker: some View {
            NativeChoicePicker(title: L("نوع نتيجة المحادثة"), selection: $session.format, choices: [
                .init(value: "discussion", label: L("نقاش")),
                .init(value: "x_posts", label: L("منشورات X")),
                .init(value: "youtube_long", label: L("YouTube طويل")),
                .init(value: "tiktok", label: "TikTok")
            ]).fixedSize()
    }
    private var modelPickerButton: some View {
            Button { modelOptions.toggle() } label: {
                HStack(spacing: 7) {
                    Image(systemName: "cpu")
                    Text(session.modelID.isEmpty ? L("اختر نموذجًا") : DisplayFormat.isolated(session.modelID)).lineLimit(1)
                }
            }.buttonStyle(.borderless)
                .accessibilityLabel(L("اختيار النموذج والاتصال"))
                .popover(isPresented: $modelOptions) {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(L("النموذج والاتصال")).font(.headline)
                        if model.snapshot?.profiles.isEmpty != false {
                            Text(L("اختر نموذجًا لبدء المحادثة."))
                            Button(L("الإعدادات…")) { modelOptions = false; openSettings() }
                        } else {
                            ConnectionModelPicker(profileID: $session.profileID, modelID: $session.modelID, ready: $session.modelReady)
                                .id(session.agentID).disabled(!session.agentID.isEmpty)
                            if !session.agentID.isEmpty { Text(L("لتغيير نموذج هذا الوكيل، افتح إعدادات الوكلاء.")).font(.caption).foregroundStyle(.secondary) }
                        }
                        HStack { Spacer(); Button(L("تم")) { modelOptions = false } }
                    }.padding(24).frame(width: 430).editorialPresentation()
                }
    }
    private var composer: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 10) {
                ZStack(alignment: .topLeading) {
                    if session.composer.isEmpty {
                        Text(L("اكتب طلبك أو ناقش فكرة…")).foregroundStyle(.secondary).padding(5).allowsHitTesting(false)
                    }
                    ChatComposer(text: $session.composer, canSend: canSend) {
                        Task { await session.send(model, articleIDs: selectedArticleIDs, draftText: draftText, draftTitle: draftTitle) }
                    }
                        .accessibilityLabel(L("رسالة المحادثة"))
                        .frame(height: isWelcome ? 96 : 72)
                }
                HStack(spacing: 12) {
                    Button { contextOptions.toggle() } label: { Image(systemName: "plus.circle") }
                        .buttonStyle(.borderless).help(L("المراجع وخيارات الكتابة"))
                        .accessibilityLabel(L("المراجع وخيارات الكتابة"))
                        .popover(isPresented: $contextOptions) { contextControls.editorialPresentation() }
                    outputPicker
                    modelPickerButton
                    Spacer(minLength: 0)
                    if session.sending, let job = session.jobID {
                        Button(L("إيقاف"), systemImage: "stop.fill") { Task { await model.perform("jobs.cancel", ["job_id": job]) } }
                    } else {
                        Button { Task { await session.send(model, articleIDs: selectedArticleIDs, draftText: draftText, draftTitle: draftTitle) } } label: {
                            Image(systemName: "arrow.up").font(.body.weight(.semibold)).frame(width: 22, height: 22)
                        }.buttonStyle(.borderedProminent).disabled(!canSend)
                            .accessibilityLabel(L("إرسال")).help(L("إرسال (Enter) · سطر جديد (Shift+Enter)"))
                            .keyboardShortcut(.return, modifiers: .command)
                    }
                }
            }.padding(16).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 16))
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(nsColor: .separatorColor).opacity(0.6)))
            if !modelPermission { ModelPermissionNotice() }
            else if session.profileID.isEmpty || session.modelID.isEmpty {
                HStack { Text(L("اختر نموذجًا لبدء المحادثة.")).foregroundStyle(.secondary); Button(L("الإعدادات")) { openSettings() } }
            }
            if session.useNews || session.includeDraft {
                HStack(spacing: 12) {
                    if session.useNews { Label(selectedArticleIDs.isEmpty ? L("أخبار آخر 7 أيام") : L("الأخبار المحددة ({0})", selectedArticleIDs.count), systemImage: "newspaper") }
                    if session.useNews && (session.researchWeb || ChatResearchIntent.requiresCurrentNews(session.composer)) {
                        Label(L("بحث مباشر عن أخبار حديثة"), systemImage: "magnifyingglass")
                    }
                    if session.includeDraft { Label(L("المسودة الحالية"), systemImage: "doc.text") }
                }.font(.caption).foregroundStyle(.secondary)
            }
            if let attachedArticle, selectedArticleIDs.contains(attachedArticle.articleId) {
                HStack(spacing: 8) {
                    Label(attachedArticle.title, systemImage: "link").lineLimit(1)
                    Button { selectedArticleIDs.remove(attachedArticle.articleId); self.attachedArticle = nil } label: {
                        Image(systemName: "xmark.circle.fill")
                    }.buttonStyle(.borderless).accessibilityLabel(L("إزالة المقالة المرفقة"))
                }.font(.caption).foregroundStyle(.secondary)
            }
            if session.composer.count > 12000 { Text(L("اختصر الرسالة إلى {0} حرف.", 12000)).font(.caption).foregroundStyle(.red) }
        }.disabled(session.loading)
    }
    private var contextControls: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(L("المراجع وخيارات الكتابة")).font(.headline)
            Toggle(selectedArticleIDs.isEmpty ? L("استخدم أخبار آخر {0} أيام من اشتراكاتي", 7) : L("استخدم الأخبار المحددة ({0})", selectedArticleIDs.count), isOn: $session.useNews)
            Toggle(L("ابحث عن تقارير حديثة على الويب"), isOn: $session.researchWeb)
                .disabled(!session.useNews)
            Text(L("عند طلب «آخر خبر»، يبحث التطبيق تلقائيًا. الأبحاث العامة ليست بديلًا عن التحقق من المصدر الأصلي."))
                .font(.caption).foregroundStyle(.secondary)
            if !draftText.isEmpty { Toggle(L("إرفاق المسودة الحالية للنقاش أو إعادة الصياغة"), isOn: $session.includeDraft) }
            agentPicker
            if ["youtube_long", "tiktok"].contains(session.format) {
                Stepper(L("المدة: {0} ثانية", session.seconds), value: $session.seconds, in: 10...7200, step: 10)
            }
            Button(L("إضافة مصادر للأخبار…")) { contextOptions = false; showNews() }
            Button(L("إرفاق رابط مقالة…"), systemImage: "link.badge.plus") {
                contextOptions = false; attachArticle = true
            }
        }.padding(22).frame(width: 380)
    }
    private var articleAttachmentSheet: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(L("إرفاق مقالة بالمحادثة")).font(.title2.weight(.semibold))
            Text(L("ألصق رابط المقالة العامة. سيقرأ التطبيق نصها ويضيفها إلى مراجع رسالتك التالية؛ يمكنك بعدها طلب شرحها أو استخدامها مثالًا لزاوية الكتابة."))
                .foregroundStyle(.secondary)
            TextField(L("رابط المقالة"), text: $articleURL, prompt: Text("https://example.com/article"))
                .textFieldStyle(.roundedBorder)
                .environment(\.layoutDirection, .leftToRight)
                .accessibilityLabel(L("رابط المقالة"))
            if let attachmentError {
                Label(attachmentError, systemImage: "exclamationmark.circle").foregroundStyle(.red)
            }
            HStack {
                Spacer()
                Button(L("إلغاء")) { attachArticle = false; attachmentError = nil }
                    .disabled(attaching)
                Button(L("إرفاق المقالة")) { Task { await importArticle() } }
                    .buttonStyle(.borderedProminent)
                    .disabled(attaching || !articleURL.lowercased().hasPrefix("http"))
                if attaching { ProgressView().controlSize(.small) }
            }
        }.padding(24).frame(width: 480)
    }
    private func importArticle() async {
        attaching = true; attachmentError = nil
        defer { attaching = false }
        do {
            let result = try await model.decoded("news.import", ["url": articleURL.trimmingCharacters(in: .whitespacesAndNewlines)], as: ImportedArticle.self)
            selectedArticleIDs.insert(result.articleId)
            attachedArticle = result
            session.useNews = true
            articleURL = ""
            attachArticle = false
        } catch { attachmentError = error.localizedDescription }
    }
}
