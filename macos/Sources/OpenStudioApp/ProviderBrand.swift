import SwiftUI
import AppKit

struct ProviderBrand: Decodable {
    let name: String
    let asset: String?
    let source: String?
    let license: String?
    let template: Bool?
}

enum ProviderBrands {
    static let all: [String: ProviderBrand] = {
        guard let url = Bundle.module.url(forResource: "provider-brands", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let values = try? JSONDecoder().decode([String: ProviderBrand].self, from: data) else { return [:] }
        return values
    }()

    static func logoURL(for id: String) -> URL? {
        guard let asset = all[id]?.asset else { return nil }
        return Bundle.module.url(forResource: asset, withExtension: "png")
    }
}

extension Provider {
    var displayName: String { ProviderBrands.all[id]?.name ?? name }
}

/// Offline brand marks. A missing asset gets an honest neutral monogram;
/// provider setup never contacts an icon CDN or arbitrary configured host.
struct ProviderBrandView: View {
    let provider: Provider
    var size: CGFloat = 28

    var body: some View {
        Group {
            if let url = ProviderBrands.logoURL(for: provider.id), let image = NSImage(contentsOf: url) {
                Image(nsImage: image).resizable().renderingMode(ProviderBrands.all[provider.id]?.template == false ? .original : .template).scaledToFit()
                    .foregroundStyle(.primary).padding(size * 0.12)
            } else {
                Text(String(provider.displayName.filter(\.isLetter).prefix(2)).uppercased())
                    .font(.system(size: max(9, size * 0.37), weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.quaternary, in: RoundedRectangle(cornerRadius: 5))
            }
        }
        .frame(width: size, height: size)
        .environment(\.layoutDirection, .leftToRight)
        .accessibilityHidden(true)
    }
}
