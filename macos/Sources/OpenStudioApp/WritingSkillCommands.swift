import SwiftUI

struct WritingSkill: Decodable, Identifiable {
    let id, titleAr, titleEn, descriptionAr, descriptionEn, format: String
    func title(_ language: String) -> String { language == "ar" ? titleAr : titleEn }
    func detail(_ language: String) -> String { language == "ar" ? descriptionAr : descriptionEn }
    static func matches(_ text: String, in skills: [WritingSkill]) -> [WritingSkill] {
        let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard value.hasPrefix("/"), !value.dropFirst().contains(where: { $0.isWhitespace }), !value.dropFirst().contains("/") else { return [] }
        let query = String(value.dropFirst()).lowercased()
        // A trailing space means the user already chose a command and is entering its arguments.
        guard !text.hasSuffix(" "), !text.hasSuffix("\n") else { return [] }
        return skills.filter { query.isEmpty || $0.id.lowercased().contains(query) || $0.titleAr.contains(query) || $0.titleEn.lowercased().contains(query) }
    }
}
struct WritingSkillCatalog: Decodable { let skills: [WritingSkill] }

struct WritingSkillMenu: View {
    let skills: [WritingSkill]
    let language: String
    let selected: Int
    let choose: (WritingSkill) -> Void
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L("مهارات الكتابة")).font(.caption).foregroundStyle(.secondary)
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: 2) {
                        ForEach(Array(skills.enumerated()), id: \.element.id) { index, skill in
                            Button { choose(skill) } label: {
                                HStack(spacing: 12) {
                                    Text("/" + skill.id).font(.callout.monospaced()).frame(width: 110, alignment: .leading)
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(skill.title(language)).font(.callout)
                                        Text(skill.detail(language)).font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer(minLength: 0)
                                }.padding(9).contentShape(Rectangle())
                                    .background(index == selected ? Color.accentColor.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 8))
                            }.buttonStyle(.plain).id(skill.id)
                        }
                    }
                }.frame(maxHeight: 240)
                .onChange(of: selected) { _, index in
                    if skills.indices.contains(index) { proxy.scrollTo(skills[index].id) }
                }
            }
        }.padding(10).background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
    }
}
