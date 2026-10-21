// subject_mask — cut the subject out of a still with macOS Vision (the "lift subject" model Photos uses).
//
//   swiftc -O helpers/subject_mask.swift -o ~/.cache/video-use/subject_mask
//   ~/.cache/video-use/subject_mask <in.png> <mask_out.png> [person]
//
// Writes a grayscale mask the size of the input (255 = subject). The default is foreground
// instances (VNGenerateForegroundInstanceMaskRequest, macOS 14+): the person AND what they hold
// (dumbbells), which a person-only model drops. Pass `person` for VNGeneratePersonSegmentationRequest
// (accurate). Local, no upload. For thumbnails: text goes between the background and the cutout.
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count >= 3, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("usage: subject_mask <in> <mask_out> [person]\n".data(using: .utf8)!)
    exit(2)
}
let handler = VNImageRequestHandler(cgImage: cg)
var maskBuffer: CVPixelBuffer?
if args.count > 3 && args[3] == "person" {
    let req = VNGeneratePersonSegmentationRequest()
    req.qualityLevel = .accurate
    req.outputPixelFormat = kCVPixelFormatType_OneComponent8
    try handler.perform([req])
    maskBuffer = req.results?.first?.pixelBuffer
} else {
    let req = VNGenerateForegroundInstanceMaskRequest()
    try handler.perform([req])
    guard let obs = req.results?.first else { FileHandle.standardError.write("no subject found\n".data(using: .utf8)!); exit(1) }
    maskBuffer = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
}
guard let mb = maskBuffer else { exit(1) }
var ci = CIImage(cvPixelBuffer: mb)
// scale the mask to the input size (person segmentation returns a smaller buffer)
let sx = CGFloat(cg.width) / ci.extent.width, sy = CGFloat(cg.height) / ci.extent.height
ci = ci.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
let ctx = CIContext()
guard let out = ctx.createCGImage(ci, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height),
                                  format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()) else { exit(1) }
let rep = NSBitmapImageRep(cgImage: out)
try rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[2]))
print("ok \(args[2]) \(cg.width)x\(cg.height)")
