import SwiftUI

struct PickerChoice<Value: Hashable>: Identifiable {
    let value: Value
    let label: String
    var id: Value { value }
}

/// All compact choices use the system pop-up control, including in RTL layouts.
struct NativeChoicePicker<Value: Hashable>: View {
    let title: String
    @Binding var selection: Value
    let choices: [PickerChoice<Value>]

    var body: some View {
        Picker(title, selection: $selection) {
            ForEach(choices) { choice in
                Text(choice.label).tag(choice.value)
            }
        }
        .labelsHidden()
        .pickerStyle(.menu)
        .fixedSize(horizontal: true, vertical: false)
        .accessibilityLabel(title)
    }
}
