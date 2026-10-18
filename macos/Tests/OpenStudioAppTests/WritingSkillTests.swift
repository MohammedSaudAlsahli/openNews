import Testing
@testable import OpenStudioApp

@Test func slashSearchSupportsArabicAndDoesNotInterceptURLsOrArguments() {
    let skills = [WritingSkill(id: "linkedin", titleAr: "منشور مهني", titleEn: "LinkedIn post", descriptionAr: "", descriptionEn: "", format: "linkedin")]
    #expect(WritingSkill.matches("/", in: skills).count == 1)
    #expect(WritingSkill.matches("/LINK", in: skills).count == 1)
    #expect(WritingSkill.matches("/مهني", in: skills).count == 1)
    for input in ["https://example.com", "شرح /linkedin", "/linkedin write this", "/linkedin ", "/tmp/file", "/unknown"] {
        #expect(WritingSkill.matches(input, in: skills).isEmpty)
    }
}
