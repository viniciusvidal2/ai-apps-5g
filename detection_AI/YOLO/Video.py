import cv2
import base64
import numpy as np
from inference_sdk import InferenceHTTPClient
from inference_sdk.webrtc import VideoFileSource, StreamConfig, VideoMetadata

client = InferenceHTTPClient.init(
    api_url="http://localhost:9001",
    api_key="mYNkfy6QOq4vGnLEeGCn"
)

source = VideoFileSource("path/to/your/video.mp4", realtime_processing=False)  # Buffer and process all frames

VIDEO_OUTPUT = "visualization"
DATA_OUTPUTS = ["predictions"]

config = StreamConfig(
    stream_output=[], # We request all data via data_output for video files
    data_output=["visualization","predictions"]
)

session = client.webrtc.stream(
    source=source,
    workflow="find-people-helmets-glasses-vests-gloves-masks-ear-protectors-and-boots",
    workspace="curso-viso",
    image_input="image",
    config=config
)

frames = []

@session.on_data()
def on_data(data: dict, metadata: VideoMetadata):
    # print(f"Frame {metadata.frame_id} predictions: {data}")
    
    if VIDEO_OUTPUT and VIDEO_OUTPUT in data:
        timestamp_ms = metadata.pts * metadata.time_base * 1000
        img = cv2.imdecode(np.frombuffer(base64.b64decode(data[VIDEO_OUTPUT]["value"]), np.uint8), cv2.IMREAD_COLOR)
        frames.append((timestamp_ms, metadata.frame_id, img))
        print(f"Processed frame {metadata.frame_id}")
    else:
        print(f"Processed frame {metadata.frame_id} (data only)")

session.run()

if VIDEO_OUTPUT and len(frames) > 0:
    # Stitch frames into output video
    frames.sort(key=lambda x: x[1])
    fps = (len(frames) - 1) / ((frames[-1][0] - frames[0][0]) / 1000) if len(frames) > 1 else 30.0
    h, w = frames[0][2].shape[:2]
    out = cv2.VideoWriter("output.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for _, _, frame in frames:
        out.write(frame)
    out.release()
    print(f"Done! {len(frames)} frames at {fps:.1f} FPS -> output.mp4")
elif VIDEO_OUTPUT:
    print("No video frames collected.")
