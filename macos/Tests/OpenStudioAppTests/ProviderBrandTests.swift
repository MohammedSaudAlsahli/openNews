import AppKit
import Testing
@testable import OpenStudioApp

@Test func providerBrandsCoverEveryPackagedAdapterAndAssetsDecodeOffline() throws {
    #expect(ProviderBrands.all.count == 69)
    for (id, brand) in ProviderBrands.all {
        #expect(!brand.name.isEmpty)
        if brand.asset != nil {
            let url = try #require(ProviderBrands.logoURL(for: id))
            let image = try #require(NSImage(contentsOf: url))
            #expect(image.size.width > 0 && image.size.height > 0)
            #expect(brand.source?.hasPrefix("https://") == true)
            #expect(brand.license?.isEmpty == false)
        } else {
            #expect(ProviderBrands.logoURL(for: id) == nil)
            #expect(brand.source == nil)
        }
    }
    #expect(ProviderBrands.all["openai-chat"]?.name != ProviderBrands.all["openai-responses"]?.name)
    #expect(ProviderBrands.all["aws-claude"]?.name.contains("Bedrock") == true)
    #expect(ProviderBrands.all["ollama"]?.asset == ProviderBrands.all["ollama-responses"]?.asset)
}
