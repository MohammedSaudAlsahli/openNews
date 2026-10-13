import Foundation
import Testing
@testable import OpenStudioApp

@Test func healthDecodesPythonContract() throws {
    let data = Data(#"{"engine_version":"0.1.0","schema_version":1,"sqlite_vec":"v0.1.9","workspace_id":"test"}"#.utf8)
    let health = try JSONDecoder.engine.decode(Health.self,from:data)
    #expect(health.schemaVersion == 1)
    #expect(health.sqliteVec == "v0.1.9")
}

@Test func arabicEvidenceUsesCodePointOffsets() throws {
    let data = Data(#"{"id":"a","name":"سؤال","description":"شرح","applicability":"سياق","method":"local_structure","status":"suggested","evidence_text":"كَيْف نكتب؟ ثم نراجع","source_title":"مثال","canonical_uri":"","excerpt_start":0,"excerpt_end":11}"#.utf8)
    let card = try JSONDecoder.engine.decode(TechniqueCard.self,from:data)
    #expect(card.excerpt == "كَيْف نكتب؟")
}

@Test func protocolRequestIsVersioned() throws {
    let request = IPCRequest(requestID:UUID(),command:"runtime.health")
    let json = try JSONSerialization.jsonObject(with:JSONEncoder().encode(request)) as! [String:Any]
    #expect(json["schema_version"] as? Int == 1)
    #expect(json["request_id"] != nil)
}

@Test func oversizeIPCRejectedBeforeConnect() {
    #expect(throws: EngineError.self) {
        try SocketTransport.exchange(path:"/tmp/not-a-socket",data:Data(repeating:0,count:SocketTransport.maximumFrame+1))
    }
}
