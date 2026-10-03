/**
 * WebSocket manager for real-time token streaming and citation retrieval
 */

export class StreamingChatClient {
  constructor(url = 'ws://localhost:8000/ws/chat') {
    this.url = url;
    this.ws = null;
    this.callbacks = {};
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log("[WebSocket] Connected to AgriSys chat stream.");
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (this.callbacks.onMessage) {
              this.callbacks.onMessage(data);
            }
          } catch (e) {
            console.warn("[WebSocket] Received non-JSON:", event.data);
          }
        };

        this.ws.onerror = (err) => {
          console.error("[WebSocket] Connection error:", err);
          if (this.callbacks.onError) this.callbacks.onError(err);
          reject(err);
        };

        this.ws.onclose = () => {
          console.log("[WebSocket] Disconnected.");
          if (this.callbacks.onClose) this.callbacks.onClose();
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message }));
    } else {
      console.warn("[WebSocket] Cannot send message, socket not open");
    }
  }

  on(event, callback) {
    this.callbacks[event] = callback;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}
