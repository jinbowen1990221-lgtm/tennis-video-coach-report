#!/usr/bin/env swift
import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import Vision

struct PosePoint: Codable {
    let x: Double
    let y: Double
    let confidence: Double
}

struct PoseFrame: Codable {
    let frame: Int
    let time: Double
    let points: [String: PosePoint]
}

struct PoseResult: Codable {
    let backend: String
    let width: Int
    let height: Int
    let fps: Double
    let frameCount: Int
    let detectedFrames: Int
    let frames: [PoseFrame]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

guard CommandLine.arguments.count >= 3 else {
    fail("Usage: extract_pose_macos.swift <video-or-frame-dir> <output.json> [min-confidence] [stride-or-fps]")
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let minConfidence = CommandLine.arguments.count > 3 ? Double(CommandLine.arguments[3]) ?? 0.20 : 0.20
let stride = max(1, CommandLine.arguments.count > 4 ? Int(CommandLine.arguments[4]) ?? 1 : 1)

func detectedPoints(
    handler: VNImageRequestHandler,
    request: VNDetectHumanBodyPoseRequest,
    minConfidence: Double
) -> [String: PosePoint]? {
    do {
        try handler.perform([request])
    } catch {
        return nil
    }
    guard let observations = request.results, !observations.isEmpty else { return nil }

    var bestPoints: [VNHumanBodyPoseObservation.JointName: VNRecognizedPoint] = [:]
    var bestArea = 0.0
    for observation in observations {
        guard let recognized = try? observation.recognizedPoints(.all) else { continue }
        let visible = recognized.values.filter { Double($0.confidence) >= minConfidence }
        guard visible.count >= 6 else { continue }
        let xs = visible.map { Double($0.location.x) }
        let ys = visible.map { Double($0.location.y) }
        guard let minX = xs.min(), let maxX = xs.max(), let minY = ys.min(), let maxY = ys.max() else { continue }
        let area = max(0, maxX - minX) * max(0, maxY - minY)
        if area > bestArea {
            bestArea = area
            bestPoints = recognized
        }
    }
    guard !bestPoints.isEmpty else { return nil }

    var jsonPoints: [String: PosePoint] = [:]
    for (name, point) in bestPoints where Double(point.confidence) >= minConfidence {
        jsonPoints[name.rawValue.rawValue] = PosePoint(
            x: Double(point.location.x),
            y: 1.0 - Double(point.location.y),
            confidence: Double(point.confidence)
        )
    }
    return jsonPoints.count >= 6 ? jsonPoints : nil
}

func writeResult(_ result: PoseResult, to outputURL: URL) {
    do {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(result)
        try data.write(to: outputURL, options: .atomic)
    } catch {
        fail("Could not write pose JSON: \(error)")
    }
}

var isDirectory: ObjCBool = false
if FileManager.default.fileExists(atPath: inputURL.path, isDirectory: &isDirectory), isDirectory.boolValue {
    let imageURLs: [URL]
    do {
        imageURLs = try FileManager.default.contentsOfDirectory(
            at: inputURL,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ).filter { ["jpg", "jpeg", "png"].contains($0.pathExtension.lowercased()) }
         .sorted { $0.lastPathComponent < $1.lastPathComponent }
    } catch {
        fail("Could not read frame directory: \(error)")
    }
    guard let firstURL = imageURLs.first,
          let source = CGImageSourceCreateWithURL(firstURL as CFURL, nil),
          let firstImage = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        fail("No readable images found in \(inputURL.path)")
    }
    let fps = CommandLine.arguments.count > 4 ? Double(CommandLine.arguments[4]) ?? 15.0 : 15.0
    let request = VNDetectHumanBodyPoseRequest()
    var frames: [PoseFrame] = []
    for (index, url) in imageURLs.enumerated() {
        let handler = VNImageRequestHandler(url: url, orientation: .up, options: [:])
        if let points = detectedPoints(handler: handler, request: request, minConfidence: minConfidence) {
            frames.append(PoseFrame(frame: index, time: Double(index) / fps, points: points))
        }
    }
    let result = PoseResult(
        backend: "apple_vision",
        width: firstImage.width,
        height: firstImage.height,
        fps: fps,
        frameCount: imageURLs.count,
        detectedFrames: frames.count,
        frames: frames
    )
    writeResult(result, to: outputURL)
    print("Detected pose in \(frames.count)/\(max(imageURLs.count, 1)) frames")
    exit(0)
}

let asset = AVAsset(url: inputURL)
guard let track = asset.tracks(withMediaType: .video).first else {
    fail("No video track found: \(inputURL.path)")
}

let naturalSize = track.naturalSize.applying(track.preferredTransform)
let width = max(1, Int(abs(naturalSize.width).rounded()))
let height = max(1, Int(abs(naturalSize.height).rounded()))
let nominalFPS = track.nominalFrameRate > 0 ? Double(track.nominalFrameRate) : 30.0

let reader: AVAssetReader
do {
    reader = try AVAssetReader(asset: asset)
} catch {
    fail("Could not create AVAssetReader: \(error)")
}

let settings: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)
]
let output = AVAssetReaderTrackOutput(track: track, outputSettings: settings)
output.alwaysCopiesSampleData = false
guard reader.canAdd(output) else {
    fail("Could not add video output")
}
reader.add(output)
guard reader.startReading() else {
    fail("Could not start reading video: \(reader.error?.localizedDescription ?? "unknown error")")
}

let request = VNDetectHumanBodyPoseRequest()
var frameIndex = 0
var detectedFrames = 0
var frames: [PoseFrame] = []

while let sample = output.copyNextSampleBuffer() {
    defer { frameIndex += 1 }
    if frameIndex % stride != 0 { continue }
    guard let pixelBuffer = CMSampleBufferGetImageBuffer(sample) else { continue }
    let timestamp = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sample))
    let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])
    guard let jsonPoints = detectedPoints(handler: handler, request: request, minConfidence: minConfidence) else { continue }
    detectedFrames += 1
    frames.append(PoseFrame(frame: frameIndex, time: timestamp, points: jsonPoints))
}

let result = PoseResult(
    backend: "apple_vision",
    width: width,
    height: height,
    fps: nominalFPS,
    frameCount: frameIndex,
    detectedFrames: detectedFrames,
    frames: frames
)

writeResult(result, to: outputURL)

print("Detected pose in \(detectedFrames)/\(max(frameIndex, 1)) frames")
