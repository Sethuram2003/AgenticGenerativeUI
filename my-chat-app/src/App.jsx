import React from "react"; // needed for React.useState
import "@openuidev/react-ui/components.css";
import "@openuidev/react-ui/styles/index.css";
import { FullScreen } from "@openuidev/react-ui";
import { langGraphAdapter, langGraphMessageFormat } from "@openuidev/react-headless";
import { openuiChatLibrary } from "@openuidev/react-ui/genui-lib";

const systemPrompt = openuiChatLibrary.prompt();

function CustomUserMessage({ message }) {
  return (
    <div
      style={{
        alignSelf: "flex-end",
        background: "#2563eb",
        borderRadius: "12px",
        padding: "10px 14px",
        maxWidth: "75%",
        margin: "4px 0",
        color: "white",
      }}
    >
      {message.content}
    </div>
  );
}

function CustomComposer({ onSend, onCancel, isRunning, isLoadingMessages }) {
  const [text, setText] = React.useState("");

  const handleSubmit = () => {
    if (text.trim() && !isRunning) {
      onSend(text.trim());
      setText("");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "8px",
        padding: "12px",
        borderTop: "1px solid #e5e7eb",
        background: "white",
      }}
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Type your message..."
        disabled={isRunning || isLoadingMessages}
        rows={1}
        style={{
          flex: 1,
          resize: "none",
          borderRadius: "8px",
          border: "1px solid #d1d5db",
          padding: "8px 12px",
          fontFamily: "inherit",
          fontSize: "14px",
          background: isRunning ? "#f9fafb" : "white",
          color: "#111827", 
        }}
        
      />
      {isRunning ? (
        <button
          onClick={onCancel}
          style={{
            padding: "8px 16px",
            background: "#ef4444",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Stop
        </button>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || isLoadingMessages}
          style={{
            padding: "8px 16px",
            background: text.trim() ? "#2563eb" : "#9ca3af",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: text.trim() ? "pointer" : "not-allowed",
          }}
        >
          Send
        </button>
      )}
    </div>
  );
}

const welcomeMessage = {
  title: "Welcome to LangGraph Chat",
  description: "Ask me anything about your data, workflows, or agents.",
  image: <div style={{ fontSize: "48px" }}>🦜</div>,
};



export default function App() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <FullScreen
        processMessage={async ({ messages, abortController }) =>
          fetch("http://localhost:8000/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              messages: langGraphMessageFormat.toApi(messages),
              systemPrompt,
            }),
            signal: abortController.signal,
          })
        }
        streamProtocol={langGraphAdapter()}
        componentLibrary={openuiChatLibrary}
        agentName="GenerativeUI Chat"
        logoUrl="https://raw.githubusercontent.com/feathericons/feather/master/icons/message-circle.svg"
        userMessage={CustomUserMessage}
        composer={CustomComposer}
        welcomeMessage={welcomeMessage}
      />
    </div>
  );
}