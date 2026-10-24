import Foundation
import IOKit.ps
import Darwin
// Narrow native bridge: no credentials, shell commands, arbitrary paths or URLs.
func output(_ value: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: value), let text = String(data: data, encoding: .utf8) { print(text) }
}
let command = CommandLine.arguments.dropFirst().first ?? "device"
if command == "device" {
    let states = [ProcessInfo.ThermalState.nominal: "nominal", .fair: "fair", .serious: "serious", .critical: "critical"]
    var pressure: Int32 = 0
    var length = MemoryLayout<Int32>.size
    let success = sysctlbyname("kern.memorystatus_vm_pressure_level", &pressure, &length, nil, 0) == 0
    let levels: [Int32: String] = [1: "normal", 2: "warning", 4: "critical"]
    var battery: Any = NSNull()
    if let info = IOPSCopyPowerSourcesInfo()?.takeRetainedValue(),
       let source = IOPSGetProvidingPowerSourceType(info)?.takeUnretainedValue() {
        battery = (source as String) == (kIOPSBatteryPowerValue as String)
    }
    output(["thermal": states[ProcessInfo.processInfo.thermalState] ?? "unknown",
        "low_power": ProcessInfo.processInfo.isLowPowerModeEnabled,
        "on_battery": battery, "memory_pressure": success ? levels[pressure] ?? "unknown" : "unknown"])
} else {
    output(["error": "Unsupported operation"])
    exit(1)
}
