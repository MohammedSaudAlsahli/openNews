import SwiftUI

/// Shows actual tool activity, with references collected once beneath the final reply.
struct ConversationActivity: View {
    let progress: ConversationProgress
    @ObservedObject var model: StudioModel
    var body: some View {
        if let activity = progress.activity, !activity.isEmpty {
            Label(activity, systemImage: progress.stage == "reading" ? "doc.text" : "magnifyingglass")
                .font(.caption).foregroundStyle(.secondary).lineLimit(2)
                .textSelection(.enabled)
        }
    }
}
