import Foundation
// Narrow native bridge: no credentials, shell commands, arbitrary paths or URLs.
func output(_ value: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: value), let text = String(data: data, encoding: .utf8) { print(text) }
}
let command = CommandLine.arguments.dropFirst().first ?? "device"
if command == "device" {
    let states = [ProcessInfo.ThermalState.nominal: "nominal", .fair: "fair", .serious: "serious", .critical: "critical"]
    output(["thermal": states[ProcessInfo.processInfo.thermalState] ?? "unknown", "low_power": ProcessInfo.processInfo.isLowPowerModeEnabled])
} else {
    output(["error": "Unsupported operation"])
    exit(1)
}
