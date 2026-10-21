// apple_sdr — convert an iPhone HLG / Dolby Vision clip to SDR BT.709 with Apple's own pipeline.
//
//   swiftc -O helpers/apple_sdr.swift -o ~/.cache/video-use/apple_sdr
//   ~/.cache/video-use/apple_sdr <in.mov> <out.mov> [video Mbps, default 80]
//
// Why (kb/mistakes.md M054): iPhone clips are Dolby Vision 8.4 (HLG base + RPU). ffmpeg's
// zscale/tonemap reads only the HLG base, so specular highlights (the lit eyebrow) go white and
// skin goes orange. AVFoundation applies the RPU, which is what Photos shows. A video
// composition with BT.709 colour properties makes AVFoundation tone-map to SDR; the frames are
// re-encoded as HEVC at a high bitrate (a mezzanine: render.py encodes again) and tagged 709.
// Audio is copied untouched. Frame timing follows the source track, so EDL times stay valid.
import AVFoundation
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: apple_sdr <in> <out> [Mbps]\n".data(using: .utf8)!)
    exit(2)
}
let src = URL(fileURLWithPath: args[1]), dst = URL(fileURLWithPath: args[2])
let mbps = args.count > 3 ? Double(args[3])! : 80.0
try? FileManager.default.removeItem(at: dst)

let asset = AVURLAsset(url: src)
let sem = DispatchSemaphore(value: 0)
var vTrack: AVAssetTrack!, aTrack: AVAssetTrack?
var size = CGSize.zero, frameDur = CMTime(value: 1, timescale: 30), transform = CGAffineTransform.identity
Task {
    vTrack = try! await asset.loadTracks(withMediaType: .video).first!
    aTrack = try! await asset.loadTracks(withMediaType: .audio).first
    size = try! await vTrack.load(.naturalSize)
    frameDur = try! await vTrack.load(.minFrameDuration)
    transform = try! await vTrack.load(.preferredTransform)
    sem.signal()
}
sem.wait()

// The composition does the HDR -> SDR conversion: BT.709 primaries, transfer and matrix.
let comp = AVMutableVideoComposition()
// A rotated clip (iPhone portrait: preferredTransform of -90 degrees) renders at its DISPLAY size.
let shown = CGRect(origin: .zero, size: size).applying(transform)
comp.renderSize = CGSize(width: abs(shown.width), height: abs(shown.height))
let renderSize = comp.renderSize
comp.frameDuration = frameDur
comp.colorPrimaries = AVVideoColorPrimaries_ITU_R_709_2
comp.colorTransferFunction = AVVideoTransferFunction_ITU_R_709_2
comp.colorYCbCrMatrix = AVVideoYCbCrMatrix_ITU_R_709_2
let ins = AVMutableVideoCompositionInstruction()
ins.timeRange = CMTimeRange(start: .zero, duration: asset.duration)
let layer = AVMutableVideoCompositionLayerInstruction(assetTrack: vTrack)
layer.setTransform(transform, at: .zero)
ins.layerInstructions = [layer]
comp.instructions = [ins]

let reader = try! AVAssetReader(asset: asset)
let vOut = AVAssetReaderVideoCompositionOutput(videoTracks: [vTrack], videoSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr10BiPlanarVideoRange,
])
vOut.videoComposition = comp
vOut.alwaysCopiesSampleData = false
reader.add(vOut)
var aOut: AVAssetReaderTrackOutput?
if let a = aTrack {
    aOut = AVAssetReaderTrackOutput(track: a, outputSettings: nil)   // passthrough
    reader.add(aOut!)
}

let writer = try! AVAssetWriter(outputURL: dst, fileType: .mov)
let vIn = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.hevc,
    AVVideoWidthKey: Int(renderSize.width), AVVideoHeightKey: Int(renderSize.height),
    AVVideoColorPropertiesKey: [
        AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
        AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
        AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
    ],
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: Int(mbps * 1_000_000),
        AVVideoProfileLevelKey: kVTProfileLevel_HEVC_Main10_AutoLevel,
        AVVideoExpectedSourceFrameRateKey: 30,
        AVVideoMaxKeyFrameIntervalKey: 30,
    ],
])
vIn.expectsMediaDataInRealTime = false
writer.add(vIn)
var aIn: AVAssetWriterInput?
if let a = aTrack {
    var hint: CMFormatDescription?
    let s2 = DispatchSemaphore(value: 0)
    Task { hint = try! await a.load(.formatDescriptions).first; s2.signal() }
    s2.wait()
    aIn = AVAssetWriterInput(mediaType: .audio, outputSettings: nil, sourceFormatHint: hint)
    aIn!.expectsMediaDataInRealTime = false
    writer.add(aIn!)
}

reader.startReading()
writer.startWriting()
writer.startSession(atSourceTime: .zero)
let group = DispatchGroup()
func pump(_ input: AVAssetWriterInput, _ output: AVAssetReaderOutput, _ label: String) {
    group.enter()
    input.requestMediaDataWhenReady(on: DispatchQueue(label: label)) {
        while input.isReadyForMoreMediaData {
            if let sb = output.copyNextSampleBuffer() {
                if !input.append(sb) {
                    FileHandle.standardError.write("append failed (\(label)): \(String(describing: writer.error))\n".data(using: .utf8)!)
                    input.markAsFinished(); group.leave(); return
                }
            } else {
                input.markAsFinished(); group.leave(); return
            }
        }
    }
}
pump(vIn, vOut, "video")
if let ai = aIn, let ao = aOut { pump(ai, ao, "audio") }
group.wait()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
if reader.status == .failed || writer.status != .completed {
    FileHandle.standardError.write("failed: reader \(String(describing: reader.error)) writer \(String(describing: writer.error))\n".data(using: .utf8)!)
    exit(1)
}
print("ok \(dst.path)")
