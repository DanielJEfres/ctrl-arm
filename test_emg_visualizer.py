#!/usr/bin/env python3
"""
Test script for EMG Visualizer WebSocket connection
"""
import asyncio
import websockets
import json
import time

async def test_websocket_connection():
    """Test WebSocket connection to EMG controller"""
    try:
        print("Testing WebSocket connection to EMG controller...")
        
        # Connect to the WebSocket server
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to EMG WebSocket server!")
            
            # Listen for messages for 10 seconds
            print("Listening for EMG data (10 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 10:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    print(f"📊 EMG Data: EMG1={data.get('emg1', 'N/A')}, "
                          f"EMG2={data.get('emg2', 'N/A')}, "
                          f"Gesture={data.get('gesture', 'N/A')}, "
                          f"Left Activity={data.get('left_activity', 'N/A'):.1f}, "
                          f"Right Activity={data.get('right_activity', 'N/A'):.1f}")
                    
                except asyncio.TimeoutError:
                    print("⏳ Waiting for data...")
                    continue
                except Exception as e:
                    print(f"❌ Error receiving data: {e}")
                    break
            
            print("✅ Test completed successfully!")
            
    except ConnectionRefusedError:
        print("❌ Connection refused! Make sure EMG controller is running.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    print("EMG Visualizer WebSocket Test")
    print("=" * 40)
    print("Make sure to start the EMG controller first:")
    print("python backend/ml/emg_control.py")
    print("=" * 40)
    
    asyncio.run(test_websocket_connection())
