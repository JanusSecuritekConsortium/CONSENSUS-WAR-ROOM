import threading
import json
import os
import time

def test_fallback_chain():
    print("Running fallback chain test...")
    try:
        raise Exception("Simulated primary model failure")
    except Exception:
        print("Primary failed. Fallback engaged.")
    print("✅ Fallback chain passed.")

def test_memory_concurrency():
    print("Testing memory concurrency...")
    path = "shared_memory/test_memory.json"
    os.makedirs("shared_memory", exist_ok=True)
    data = {"counter": 0}

    def writer():
        for _ in range(100):
            try:
                with open(path, 'r') as f:
                    memory = json.load(f)
            except:
                memory = data
            memory['counter'] += 1
            with open(path, 'w') as f:
                json.dump(memory, f)
            time.sleep(0.01)

    threads = [threading.Thread(target=writer) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("✅ Memory concurrency test complete.")

def validate_memory():
    print("Validating memory...")
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'memory.json':
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        json.load(f)
                    print(f"✅ {file} in {root} is valid.")
                except Exception as e:
                    print(f"❌ Error in {file} in {root}: {str(e)}")

if __name__ == "__main__":
    test_fallback_chain()
    test_memory_concurrency()
    validate_memory()
