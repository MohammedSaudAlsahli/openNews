import SwiftUI

struct LocalModelChoice: Decodable, Identifiable {
    let id, name, languages, source, purpose, quality: String
    let size: Int64?
    let installed: Bool
}
struct InstalledSummaryModel: Decodable, Identifiable { let id: String; let size: Int64 }
struct LocalModelDownload: Decodable {
    let phase, model, error: String
    let completed, total: Int64
    var active: Bool { ["checking", "preparing", "downloading", "testing"].contains(phase) }
}
struct LocalModelsStatus: Decodable {
    let runtime, canStart: Bool
    let models: [LocalModelChoice]
    let installed: [InstalledSummaryModel]
    let download: LocalModelDownload
}
struct LocalModelSize: Decodable {
    let id: String
    let size, freeDisk, requiredDisk, memory, estimatedMemory: Int64
    let runtimeSize: Int64
    let fit: String
    let canDownload: Bool
}
struct ModelLibraryRow: Decodable, Identifiable, Hashable {
    let id, name, description: String
    let capabilities: [String]
    let source: String
}
struct ModelLibraryPage: Decodable { let models: [ModelLibraryRow]; let hasMore: Bool }
struct ModelVariant: Decodable, Identifiable { let id: String; let size: Int64?; let cloud: Bool }
struct ModelVariants: Decodable { let variants: [ModelVariant] }

struct LocalSummaryModels: View {
    var chooseConnected: () -> Void = {}
    @EnvironmentObject private var model: StudioModel
    @AppStorage("appLanguage") private var language = "ar"
    @State private var status: LocalModelsStatus?
    @State private var tab = "suggested"
    @State private var query = ""
    @State private var rows: [ModelLibraryRow] = []
    @State private var selected: String?
    @State private var variants: [ModelVariant] = []
    @State private var variant = ""
    @State private var plan: LocalModelSize?
    @State private var page = 1
    @State private var more = false
    @State private var loading = false
    @State private var inspecting = false
    @State private var failure: String?
    @State private var actionBusy = false

    private var selectedRow: ModelLibraryRow? { rows.first { $0.id == selected } }
    private var downloadActive: Bool { status?.download.active == true }

    var body: some View {
        VStack(spacing: 0) {
            summaryControls
            Divider()
            HStack(spacing: 0) {
                VStack(spacing: 12) {
                    Picker(L("عرض النماذج"), selection: $tab) {
                        Text(L("مقترحة")).tag("suggested")
                        Text(L("المكتبة")).tag("library")
                        Text(L("محمّلة")).tag("installed")
                    }.pickerStyle(.segmented).labelsHidden()
                    TextField(L("ابحث عن نموذج"), text: Binding(get: { query }, set: { query = $0; tab = "library" })).textFieldStyle(.roundedBorder)
                    List(selection: $selected) {
                        ForEach(rows) { row in
                            VStack(alignment: .leading, spacing: 5) {
                                Text(row.name).font(.body.weight(.medium))
                                Text(row.description).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                            }.padding(.vertical, 7).tag(row.id)
                        }
                        if more {
                            Button(L("عرض المزيد")) { Task { await search(append: true) } }.disabled(loading)
                        }
                    }.listStyle(.inset).overlay {
                        if rows.isEmpty && !loading {
                            ContentUnavailableView(L(tab == "installed" ? "لا توجد نماذج محمّلة" : "لا توجد نتائج"), systemImage: "square.stack.3d.up", description: Text(L("اختر من المقترحات أو ابحث في المكتبة.")))
                        }
                    }
                    if loading { ProgressView().controlSize(.small) }
                    HStack {
                        Text(L("من مكتبة Ollama")).font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button { Task { await search() } } label: { Image(systemName: "arrow.clockwise") }
                            .help(L("إعادة المحاولة")).buttonStyle(.borderless).disabled(loading)
                    }
                }.padding(16).frame(minWidth: 220, idealWidth: 260, maxWidth: 300)
                Divider()
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if let row = selectedRow { modelDetail(row) }
                        else {
                            ContentUnavailableView(L("اختر نموذج التلخيص"), systemImage: "text.page", description: Text(L("قارن الحجم وملاءمة جهازك، ثم حمّل وابدأ مباشرة.")))
                        }
                        if let status, status.download.phase != "idle" { downloadStatus(status.download) }
                        if let failure {
                            Label(failure, systemImage: "exclamationmark.circle").foregroundStyle(.red).font(.callout).textSelection(.enabled)
                        }
                    }.padding(24).frame(maxWidth: .infinity, alignment: .leading)
                }.frame(minWidth: 310, maxWidth: .infinity)
            }
        }
        .task {
            while !Task.isCancelled {
                do {
                    status = try await model.decoded("news.local.status", as: LocalModelsStatus.self)
                    let next = try await model.decoded("news.digest.status", as: NewsDigestStatus.self)
                    if next != model.digestStatus { model.digestStatus = next }
                    try await Task.sleep(for: .seconds(2))
                } catch is CancellationError { return }
                catch { failure = error.localizedDescription; try? await Task.sleep(for: .seconds(5)) }
            }
        }
        .task(id: tab + "|" + query) {
            do { try await Task.sleep(for: .milliseconds(300)) } catch { return }
            await search()
        }
        .task(id: selected) { await loadVariants() }
        .task(id: variant) { await inspectVariant() }
    }

    private var summaryControls: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 5) {
                    Text(L("التلخيص التلقائي")).font(.headline)
                    Text(currentModel).font(.callout).foregroundStyle(.secondary).lineLimit(1)
                }
                Spacer()
                Menu {
                    Button(L("استخدام نموذج متصل")) {
                        updateSettings(["engine":"provider","enabled":false])
                        chooseConnected()
                    }
                } label: { Image(systemName: "ellipsis") }.menuStyle(.borderlessButton).fixedSize().help(L("خيارات التلخيص"))
                Picker(L("لغة الملخصات"), selection: Binding(get: { model.digestStatus?.language ?? language }, set: { updateSettings(["language": $0]) })) {
                    Text("العربية").tag("ar"); Text("English").tag("en")
                }.fixedSize()
                Toggle(L("التلخيص التلقائي"), isOn: Binding(get: { model.digestStatus?.enabled == true }, set: { updateSettings(["enabled": $0]) }))
                    .labelsHidden().toggleStyle(.switch).disabled(actionBusy || !ModelPermission.allowed() || currentModel.isEmpty)
            }
            if let digest = model.digestStatus {
                HStack(spacing: 16) {
                    Label(L("{0} ملخص جاهز", DisplayFormat.integer(digest.prepared)), systemImage: "checkmark.circle")
                    Text(L("{0} بانتظار التلخيص", DisplayFormat.integer(digest.pending)))
                    Spacer()
                }.font(.caption).foregroundStyle(.secondary)
            }
            if let digest = model.digestStatus {
                Text(summaryPhase(digest.phase ?? "")).font(.caption).foregroundStyle(.secondary)
            }
            if model.digestStatus?.engine == "local" {
                Label(L("تلخيص هادئ: مقال واحد ثم راحة، مع إيقاف تلقائي عند ارتفاع الحرارة وتفريغ النموذج بعد العمل."), systemImage: "leaf")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            if model.digestStatus?.engine == "provider" {
                DisclosureGroup(L("خيارات النموذج المتصل")) {
                    Stepper(L("حد الملخصات اليومي") + ": \(model.digestStatus?.dailyLimit ?? 20)", value: Binding(get: { model.digestStatus?.dailyLimit ?? 20 }, set: { updateSettings(["daily_limit":$0]) }), in: 1...200)
                        .font(.callout).disabled(actionBusy)
                }.font(.caption)
            }
            if !ModelPermission.allowed() { Text(L("فعّل إذن استخدام النماذج من الصلاحيات لتشغيل التلخيص.")).font(.caption).foregroundStyle(.secondary) }
        }.padding(.horizontal, 24).padding(.vertical, 16)
    }

    private func summaryPhase(_ phase: String) -> String {
        let key: String
        switch phase {
        case "resting": key = "راحة بين الملخصات لتخفيف استهلاك الجهاز"
        case "cooling": key = "متوقف مؤقتًا حتى تنخفض حرارة الجهاز"
        case "low_power": key = "متوقف مؤقتًا أثناء وضع توفير الطاقة"
        case "waiting_device": key = "بانتظار التحقق من حالة الجهاز"
        case "disabled": key = "التلخيص التلقائي متوقف"
        case "needs_model": key = "اختر نموذجًا متاحًا للتلخيص"
        case "needs_download": key = "اختر نموذج التلخيص"
        case "daily_limit": key = "اكتمل الحد اليومي؛ يستأنف التلخيص غدًا"
        case "waiting_model": key = "بانتظار انتهاء طلبك؛ المحادثة لها الأولوية"
        case "retrying": key = "تعذّر التلخيص؛ ستتم إعادة المحاولة تلقائيًا"
        case "waiting_articles": key = "بانتظار وصول نصوص المقالات الكاملة"
        case "ready": key = "كل المقالات المتاحة ملخصة"
        case "summarizing": key = "جارٍ تجهيز الملخصات"
        default: key = "مقالات جاهزة للتلخيص في الخلفية"
        }
        return L(key)
    }

    private var currentModel: String {
        if model.digestStatus?.engine == "local" { return model.digestStatus?.localModel ?? "" }
        return model.snapshot?.assignments?.first(where: { $0.role == "news" })?.modelId ?? ""
    }

    @ViewBuilder private func modelDetail(_ row: ModelLibraryRow) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(row.name).font(.title2.weight(.semibold)).textSelection(.enabled)
            Text(row.description).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
        if row.capabilities.contains("embedding") {
            Label(L("هذا النموذج للبحث، وليس لكتابة الملخصات."), systemImage: "info.circle").font(.callout)
        } else if !variants.isEmpty {
            if variants.count > 1 {
            Picker(L("الحجم والإصدار"), selection: $variant) {
                ForEach(variants) { version in
                    Text(variantLabel(version)).tag(version.id)
                }
            }.pickerStyle(.menu)
            }
            if variants.first(where: { $0.id == variant })?.cloud == true {
                Label(L("هذا إصدار سحابي؛ اختر إصدارًا قابلًا للتحميل."), systemImage: "cloud").font(.callout)
            } else if let plan {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text(bytes(plan.size)).font(.title.weight(.semibold)).monospacedDigit()
                        Text(L("حجم التحميل")).font(.callout).foregroundStyle(.secondary)
                    }
                    Label(L(plan.fit == "fits" ? "يناسب جهازك مبدئيًا" : plan.fit == "disk" ? "المساحة لا تكفي" : "يحتاج جهازًا بذاكرة أكبر"), systemImage: plan.fit == "fits" ? "checkmark.circle" : "exclamationmark.circle")
                        .foregroundStyle(plan.canDownload ? Color.primary : Color.orange)
                    if plan.fit == "disk" {
                        Text(L("المتاح {0}، والمطلوب {1}. حرّر مساحة أو اختر حجمًا أصغر.", bytes(plan.freeDisk), bytes(plan.requiredDisk))).font(.callout)
                    } else if plan.fit == "memory" {
                        Text(L("اختر نسخة أصغر ليبقى جهازك مستجيبًا أثناء التلخيص.")).font(.callout)
                    } else {
                        Text(L("نجهّز كل ما يحتاجه، ثم نختبر تشغيله ونبدأ التلخيص تلقائيًا.")).font(.callout).foregroundStyle(.secondary)
                    }
                    Button(L(currentModel == variant && model.digestStatus?.enabled == true ? "يُستخدم الآن" : status?.installed.contains(where: { $0.id == variant }) == true ? "استخدام هذا النموذج" : "تحميل واستخدام")) { activate() }
                        .buttonStyle(.borderedProminent).controlSize(.large)
                        .disabled(!plan.canDownload || downloadActive || actionBusy || !ModelPermission.allowed() || (currentModel == variant && model.digestStatus?.enabled == true))
                }
                DisclosureGroup(L("تفاصيل الملاءمة والجودة")) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(plan.id).font(.caption).textSelection(.enabled)
                        LabeledContent(L("مساحة مطلوبة مع هامش أمان"), value: bytes(plan.requiredDisk))
                        LabeledContent(L("ذاكرة جهازك"), value: bytes(plan.memory))
                        LabeledContent(L("ذاكرة تشغيل تقديرية"), value: bytes(plan.estimatedMemory))
                        Text(L("تقدير الملاءمة ليس ضمانًا للسرعة. نتحقق من التشغيل قبل تفعيل النموذج. جودة التلخيص بالعربية والإنجليزية لم تُقاس داخل التطبيق بعد."))
                            .font(.caption).foregroundStyle(.secondary)
                        if let url = URL(string: row.source) { Link(L("معلومات النموذج"), destination: url) }
                    }.padding(.top, 8)
                }.font(.callout)
            } else if inspecting { ProgressView(L("نفحص ملاءمة جهازك…")) }
        } else if inspecting { ProgressView() }
    }

    @ViewBuilder private func downloadStatus(_ download: LocalModelDownload) -> some View {
        Divider()
        VStack(alignment: .leading, spacing: 10) {
            Text(download.model).font(.callout.weight(.medium)).lineLimit(1)
            Text(L(download.phase == "checking" ? "نفحص المساحة والذاكرة…" : download.phase == "preparing" ? "نجهّز التلخيص على جهازك…" : download.phase == "testing" ? "نتحقق من التشغيل قبل البدء…" : download.phase == "downloading" ? "جارٍ التحميل…" : download.phase == "ready" ? "جاهز؛ بدأ التلخيص التلقائي" : download.phase == "cancelled" ? "توقف التحميل" : download.error))
                .font(.callout).foregroundStyle(.secondary)
            if download.active {
                if download.total > 0 && ["preparing", "downloading"].contains(download.phase) {
                    ProgressView(value: Double(download.completed), total: Double(download.total))
                    Text(bytes(download.completed) + " / " + bytes(download.total)).font(.caption).monospacedDigit()
                } else { ProgressView().controlSize(.small) }
                Button(L("إلغاء")) { perform("news.local.cancel") }
            }
        }
    }
    private func search(append: Bool = false) async {
        let requestedTab = tab, requestedQuery = query
        loading = true; failure = nil
        defer { loading = false }
        do {
            var results: [ModelLibraryRow]
            if tab == "library" {
                let next = append ? page+1 : 1
                let result = try await model.decoded("news.local.search", ["query":query,"page":next], as: ModelLibraryPage.self)
                guard !Task.isCancelled, requestedTab == tab, requestedQuery == query else { return }
                page = next; more = result.hasMore; results = result.models
            } else {
                let state = try await model.decoded("news.local.status", as: LocalModelsStatus.self)
                guard !Task.isCancelled, requestedTab == tab, requestedQuery == query else { return }
                status = state; more = false
                results = tab == "installed" ? state.installed.map { ModelLibraryRow(id:$0.id,name:$0.id,description:bytes($0.size),capabilities:[],source:"https://ollama.com/library") } : state.models.map { ModelLibraryRow(id:$0.id,name:$0.name,description:L("تلخيص بالعربية والإنجليزية · مرشح للتجربة"),capabilities:[],source:$0.source) }
            }
            if append { let existing = Set(rows.map(\.id)); rows += results.filter { !existing.contains($0.id) } }
            else { rows = results; selected = results.first?.id }
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
    private func loadVariants() async {
        variants = []; variant = ""; plan = nil; failure = nil
        guard let row = selectedRow, !row.capabilities.contains("embedding") else { return }
        inspecting = true
        defer { inspecting = false }
        do {
            let result: [ModelVariant]
            if row.id.contains(":") { result = [ModelVariant(id:row.id,size:nil,cloud:false)] }
            else { result = try await model.decoded("news.local.variants", ["model":row.id], as: ModelVariants.self).variants }
            guard !Task.isCancelled, selected == row.id else { return }
            variants = result
            variant = result.first(where: { !$0.cloud })?.id ?? result.first?.id ?? ""
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
    private func inspectVariant() async {
        plan = nil
        let name = variant
        guard !name.isEmpty, variants.first(where: { $0.id == name })?.cloud != true else { return }
        inspecting = true; failure = nil
        defer { inspecting = false }
        do {
            let result = try await model.decoded("news.local.inspect", ["model":name], as: LocalModelSize.self)
            guard !Task.isCancelled, name == variant else { return }
            plan = result
        } catch { if !Task.isCancelled { failure = error.localizedDescription } }
    }
    private func activate() {
        perform("news.local.download", ["model":variant,"language":model.digestStatus?.language ?? language,"consent":true])
    }
    private func updateSettings(_ values: [String: Any]) {
        var payload: [String: Any] = ["enabled":model.digestStatus?.enabled == true]
        payload.merge(values) { _, new in new }
        perform("news.digest.set",payload)
    }
    private func perform(_ command: String, _ payload: [String: Any] = [:]) {
        actionBusy = true; failure = nil
        Task {
            defer { actionBusy = false }
            do {
                _ = try await model.call(command,payload)
                status = try await model.decoded("news.local.status", as: LocalModelsStatus.self)
                model.digestStatus = try await model.decoded("news.digest.status", as: NewsDigestStatus.self)
            } catch { failure = error.localizedDescription }
        }
    }
    private func bytes(_ value: Int64) -> String { ByteCountFormatter.string(fromByteCount:value,countStyle:.file) }
    private func variantLabel(_ value: ModelVariant) -> String {
        let tag = value.id.split(separator: ":").last.map(String.init) ?? value.id
        let title = value.cloud ? L("سحابي") + " · " + tag : tag == "latest" ? L("الإصدار القياسي") : tag
        return title + (value.size.map { " · " + bytes($0) } ?? "")
    }
}
