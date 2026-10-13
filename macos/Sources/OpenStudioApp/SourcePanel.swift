import SwiftUI

enum ReferenceSection: String, CaseIterable {
    case news = "الأخبار"
    case sources = "كتاباتي"
    case style = "أسلوبي"
}

struct SourcePanel: View {
    @AppStorage("appLanguage") private var interfaceLanguage = "ar"
    @EnvironmentObject var model: StudioModel
    @Binding var section: ReferenceSection
    @Binding var selectedSourceID: String?
    @Binding var selectedArticleIDs: Set<String>
    var importSource: () -> Void
    @State private var query = ""
    @State private var detail: SourceDetail?
    @State private var loading = false
    @State private var detailError: String?
    @State private var analysisSource: Source?
    @State private var retiringRule: DNARule?
    @State private var confirmingRetirement = false
    @State private var readingSource = false

    private var source: Source? { model.snapshot?.sources.first { $0.id == selectedSourceID } }
    private var sources: [Source] {
        (model.snapshot?.sources ?? []).filter { query.isEmpty || $0.title.localizedCaseInsensitiveContains(query) }
    }
    private var rules: [DNARule] { (model.snapshot?.rules ?? []).filter { $0.status == "approved" } }
    private var refreshKey: String {
        let selected = selectedSourceID ?? ""
        let version = source?.currentVersionId ?? ""
        let jobs: [Job] = model.snapshot?.jobs ?? []
        let jobStates = jobs.map { $0.id + $0.state }.joined()
        let dna = model.snapshot?.dnaVersion.id ?? ""
        return [selected, version, jobStates, dna].joined(separator: "|")
    }

    var body: some View {
        let _ = interfaceLanguage
        VStack(spacing: 0) {
            Picker(L("المراجع والأسلوب"), selection: $section) {
                ForEach(ReferenceSection.allCases, id: \.self) { Text(L($0.rawValue)).tag($0) }
            }.pickerStyle(.segmented).labelsHidden().padding(16)
            Divider()
            if section == .news {
                NewsPanel(selectedArticleIDs: $selectedArticleIDs)
            } else if section == .style {
                styleContent
            } else if let source {
                sourceContent(source)
            } else {
                sourceList
            }
        }
        .background(Color(nsColor: .controlBackgroundColor))
        .task(id: refreshKey) { await loadSource() }
        .sheet(isPresented: $readingSource) {
            if let source, let detail {
                ReadingSheet(title: source.title) {
                    ScrollView {
                        ReadingColumn {
                            VStack(alignment: .leading, spacing: 20) {
                                ProseText(text: detail.text, fontSize: 17, lineSpacing: 7)
                            }
                        }
                    }
                }
            }
        }
        .sheet(item: $analysisSource) { AnalyzeSourceSheet(source: $0) }
        .confirmationDialog(L("إزالة القاعدة من أسلوبك؟"), isPresented: $confirmingRetirement, titleVisibility: .visible) {
            Button(L("إزالة القاعدة"), role: .destructive) {
                guard let rule = retiringRule else { return }
                Task { await model.perform("dna.retire", ["rule_id": rule.id], message: L("أُزيلت القاعدة من أسلوبك.")) }
            }
            Button(L("إلغاء"), role: .cancel) {}
        } message: { Text(L("ستتوقف عن استخدامها في المسودات الجديدة. تبقى النسخ السابقة محفوظة.")) }
    }

    private var sourceList: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField(L("ابحث بعنوان المصدر"), text: $query).textFieldStyle(.plain)
            }.padding(10).background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 6)).padding(16)
            if sources.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text(query.isEmpty ? L("كتاباتك هي مرجع أسلوبك") : L("لا توجد نتائج")).font(.headline)
                    Text(query.isEmpty ? L("أضف أمثلة من كتابتك لتراجع تقنياتها. اشتراكات الأخبار منفصلة في تبويب الأخبار.") : L("جرّب عنوانًا آخر."))
                        .font(.callout).foregroundStyle(.secondary)
                    if query.isEmpty { Button(L("أضف مصدرًا"), action: importSource).disabled(model.health == nil) }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(16)
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(sources) { item in
                            Button { selectedSourceID = item.id } label: {
                                HStack(alignment: .top, spacing: 10) {
                                    Image(systemName: "doc.text").foregroundStyle(.secondary).padding(.top, 2)
                                    VStack(alignment: .leading, spacing: 5) {
                                        Text(item.title).font(.body.weight(.medium)).foregroundStyle(.primary).lineLimit(2)
                                        Text((item.purpose == "reference" ? L("مرجع للمحتوى") : L("مثال من كتاباتي")) + " · " + (item.analyses > 0 ? L("تم التحليل") : L("جاهز للمراجعة")))
                                            .font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer(minLength: 0)
                                    Image(systemName: "chevron.forward").font(.caption).foregroundStyle(.tertiary)
                                }.padding(.horizontal, 16).padding(.vertical, 12).contentShape(Rectangle())
                            }.buttonStyle(.plain)
                            Divider().padding(.horizontal, 16)
                        }
                    }
                }
            }
            Divider()
            Button(action: importSource) { Label(L("إضافة نص من كتاباتي"), systemImage: "plus") }
                .frame(maxWidth: .infinity, alignment: .leading).padding(16).disabled(model.health == nil)
        }
    }

    private func sourceContent(_ source: Source) -> some View {
        ScrollView {
            ReadingColumn {
                VStack(alignment: .leading, spacing: 16) {
                    Button { selectedSourceID = nil } label: { Label(L("كل المصادر"), systemImage: "chevron.backward") }
                        .buttonStyle(.plain).foregroundStyle(.secondary)
                    VStack(alignment: .leading, spacing: 5) {
                        Text(source.title).font(.title3.weight(.semibold)).textSelection(.enabled)
                        Text(source.purpose == "reference" ? L("مرجع للمحتوى") : L("من كتاباتي — مرجع للأسلوب")).font(.caption).foregroundStyle(.secondary)
                        if !source.author.isEmpty { Text(source.author).font(.caption).foregroundStyle(.secondary) }
                    }
                    if loading && detail == nil { ProgressView(L("جارٍ فتح المصدر…")).controlSize(.small) }
                    if let detailError {
                        Text(L(detailError)).font(.callout).foregroundStyle(.secondary)
                        Button(L("حاول مجددًا")) { Task { await loadSource() } }
                    }
                    if let detail {
                        Button { readingSource = true } label: {
                        Label(L("فتح نافذة القراءة"), systemImage: "arrow.up.left.and.arrow.down.right")
                    }.buttonStyle(.bordered)
                    DisclosureGroup(L("النص الكامل")) {
                            ProseText(text: detail.text, fontSize: 15)
                                .frame(maxWidth: .infinity, alignment: .leading).padding(.top, 8)
                        }
                        if let url = URL(string: source.canonicalUri), !source.canonicalUri.isEmpty {
                            Link(L("فتح الرابط الأصلي"), destination: url).font(.caption)
                        }
                        Divider()
                        VStack(alignment: .leading, spacing: 9) {
                            Button(source.analyses > 0 ? L("فحص التحديثات") : L("حلّل النص")) { analyzeLocally(source) }
                                .disabled(model.busy || model.health == nil)
                            Text(L("فحص محلي للسؤال الافتتاحي والخطوات والفقرات. لا يُرسل النص خارج جهازك."))
                                .font(.caption).foregroundStyle(.secondary)
                            if source.rightsStatus == "unknown" {
                                Text(L("للتحليل بالذكاء الاصطناعي، أعد استيراد النص مع تحديد ملكيته أو ترخيصه."))
                                    .font(.caption).foregroundStyle(.secondary)
                            } else {
                                Button(L("تحليل بالذكاء الاصطناعي…")) { analysisSource = source }
                                    .font(.caption).disabled(model.busy || model.health == nil)
                            }
                        }
                        Divider()
                        Text(L("اقتراحات لأسلوبك")).font(.headline)
                        if detail.techniques.isEmpty {
                            Text(source.analyses > 0 ? L("لم نجد اقتراحات بنيوية في هذا النص. جرّب مثالًا آخر، أو تحليلًا بالذكاء الاصطناعي.") : L("حلّل النص لتظهر الاقتراحات هنا. أنت تختار ما يُضاف إلى أسلوبك."))
                                .font(.callout).foregroundStyle(.secondary)
                        }
                        ForEach(detail.techniques) { technique in
                            SourceTechniqueSuggestion(technique: technique)
                            Divider()
                        }
                    }
                }
            }
        }.id(source.id)
    }

    private var styleContent: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(L("قواعد تختارها أنت")).font(.headline)
                Text(L("تُستخدم هذه القواعد عند إنشاء مسودة بالذكاء الاصطناعي."))
                    .font(.callout).foregroundStyle(.secondary)
                if rules.isEmpty {
                    Text(L("لم تضف قواعد بعد. افتح مصدرًا وراجع الاقتراحات المستخرجة منه.")).font(.callout).foregroundStyle(.secondary)
                    Button(L("اختر من المصادر")) { section = .sources }
                }
                ForEach(rules) { rule in
                    VStack(alignment: .leading, spacing: 9) {
                        Text(rule.statement).font(.body).textSelection(.enabled)
                        Button(L("إزالة من أسلوبي"), role: .destructive) {
                            retiringRule = rule
                            confirmingRetirement = true
                        }.font(.caption).disabled(model.busy)
                    }
                    Divider()
                }
            }.padding(16)
        }
    }

    private func loadSource() async {
        guard let id = selectedSourceID else { detail = nil; detailError = nil; return }
        if detail?.versionId != source?.currentVersionId { detail = nil }
        loading = true
        detailError = nil
        do {
            let loaded = try await model.decoded("sources.detail", ["item_id": id], as: SourceDetail.self)
            guard !Task.isCancelled, selectedSourceID == id else { return }
            detail = loaded
        } catch {
            guard !Task.isCancelled, selectedSourceID == id else { return }
            detailError = L("تعذّر فتح المصدر. حاول مجددًا.")
        }
        if selectedSourceID == id { loading = false }
    }

    private func analyzeLocally(_ source: Source) {
        Task {
            await model.perform("analysis.run", ["item_ids": [source.id], "mode": "incremental", "idempotency_key": UUID().uuidString], message: source.analyses > 0 ? L("النص المحلّل سابقًا لا يُعاد تحليله ما لم يتغير.") : L("بدأ التحليل. ستظهر الاقتراحات هنا عند اكتماله."))
        }
    }
}
