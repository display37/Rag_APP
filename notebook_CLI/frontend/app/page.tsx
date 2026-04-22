"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Source = {
  page: number;
  text: string;
};

type Message = {
  role: "user" | "bot";
  text: string;
  sources?: Source[];
};

type Chat = {
  id: number;
  title: string;
  last_message?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ----------------------------
  // LOAD CHAT LIST
  // ----------------------------
  const loadChats = () => {
    if (!userEmail) return;
    fetch(`${API_URL}/chat/list?email=${encodeURIComponent(userEmail)}`)
      .then((res) => res.json())
      .then((data) => {
        setChats(data);
        if (data.length > 0 && !activeChatId) setActiveChatId(data[0].id);
      });
  };

  useEffect(() => {
    loadChats();
  }, [userEmail]);

  // ----------------------------
  // LOAD CHAT HISTORY
  // ----------------------------
  useEffect(() => {
    if (!activeChatId) return;

    fetch(`${API_URL}/chat/history/${activeChatId}`)
      .then((res) => res.json())
      .then((data) => {
        setMessages(data);
      });
  }, [activeChatId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ----------------------------
  // CREATE NEW CHAT
  // ----------------------------
  const createChat = async () => {
    if (!userEmail) return null;
    const res = await fetch(`${API_URL}/chat/create?email=${encodeURIComponent(userEmail)}`, {
      method: "POST",
    });

    const data = await res.json();

    setChats((prev) => [...prev, { id: data.chat_id, title: "New Chat" }]);
    setActiveChatId(data.chat_id);
    setMessages([]);
    return data.chat_id;
  };

  // ----------------------------
  // DELETE CHAT
  // ----------------------------
  const deleteChat = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const res = await fetch(`${API_URL}/chat/delete/${id}`, {
      method: "DELETE",
    });
    if (res.ok) {
      setChats((prev) => prev.filter((c) => c.id !== id));
      if (activeChatId === id) {
        setActiveChatId(null);
        setMessages([]);
      }
    }
  };

  // ----------------------------
  // UPLOAD FILE
  // ----------------------------
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];

    let targetChatId = activeChatId;
    if (!targetChatId) {
      targetChatId = await createChat();
      if (!targetChatId) return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    try {
      const res = await fetch(
        `${API_URL}/upload/${targetChatId}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (res.ok) {
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: "📄 Document uploaded and indexed successfully! You can now ask questions about it." },
        ]);
      } else {
        alert("File upload failed.");
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading file.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // ----------------------------
  // SEND MESSAGE
  // ----------------------------
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const currentInput = input;
    setInput("");

    let targetChatId = activeChatId;
    if (!targetChatId) {
      targetChatId = await createChat();
      if (!targetChatId) {
        setInput(currentInput);
        return;
      }
    }

    const userMsg: Message = { role: "user", text: currentInput };
    const botMsg: Message = { role: "bot", text: "" };
    setMessages((prev) => [...prev, userMsg, botMsg]);
    setLoading(true);

    let botText = "";

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: currentInput,
          history: messages.map((m) => ({ role: m.role, text: m.text })), // don't send sources back to backend
          chat_id: targetChatId,
        }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader!.read();
        done = doneReading;

        const chunk = decoder.decode(value, { stream: true });
        botText += chunk;

        let displayText = botText;
        let displaySources: Source[] | undefined = undefined;

        // Parse ###SOURCES### if present
        if (botText.includes("###SOURCES###")) {
          const parts = botText.split("###SOURCES###");
          displayText = parts[0];
          try {
            displaySources = JSON.parse(parts[1]);
          } catch (e) {
            // JSON might be incomplete while streaming
          }
        }

        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            text: displayText,
            sources: displaySources,
          };
          return newMessages;
        });
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Error connecting to the server." },
      ]);
    }

    setLoading(false);
    loadChats(); // Refresh chat list to get updated title and last_message
  };

  if (!userEmail) {
    return (
      <div className="flex h-screen bg-[#212121] text-white items-center justify-center">
        <div className="bg-[#171717] p-8 rounded-xl flex flex-col gap-4 w-96 shadow-xl border border-white/10">
          <h1 className="text-2xl font-bold text-center">Login</h1>
          <p className="text-gray-400 text-sm text-center">Enter your email to continue</p>
          <input
            type="email"
            className="p-3 rounded bg-[#2f2f2f] outline-none text-white w-full"
            placeholder="Email address"
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && emailInput.includes("@")) setUserEmail(emailInput);
            }}
          />
          <button
            onClick={() => {
              if (emailInput.includes("@")) setUserEmail(emailInput);
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded transition-colors"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#212121] text-white">
      {/* SIDEBAR */}
      <aside className="w-64 bg-[#171717] p-4 flex flex-col">
        <button
          onClick={createChat}
          className="border border-white/20 p-2 rounded mb-4 hover:bg-white/10"
        >
          + New chat
        </button>

        <div className="flex-1 space-y-2 overflow-y-auto">
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setActiveChatId(chat.id)}
              className={`p-2 rounded cursor-pointer group flex justify-between items-center ${
                activeChatId === chat.id ? "bg-white/20" : "hover:bg-white/10"
              }`}
            >
              <div className="flex-1 truncate pr-2">
                <div className="font-semibold truncate">{chat.title}</div>
                {chat.last_message && (
                  <div className="text-xs text-gray-400 truncate">
                    {chat.last_message}
                  </div>
                )}
              </div>
              <button
                onClick={(e) => deleteChat(chat.id, e)}
                className="text-gray-500 hover:text-red-500 opacity-0 group-hover:opacity-100 px-1"
                title="Delete Chat"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* MAIN */}
      <main className="flex-1 flex flex-col">
        {/* MESSAGES */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-xl px-4 py-3 rounded-2xl ${
                  msg.role === "user" ? "bg-blue-600" : "bg-[#2f2f2f]"
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.text}
                </ReactMarkdown>

                {/* SOURCES RENDERER */}
                {msg.sources && msg.sources.length > 0 && (
                  <details className="mt-4 pt-3 border-t border-white/10 text-xs group">
                    <summary className="font-semibold text-gray-300 mb-2 cursor-pointer outline-none select-none hover:text-white transition-colors">
                      View Sources ({msg.sources.length})
                    </summary>
                    <div className="flex flex-col gap-2 mt-2">
                      {msg.sources.map((src, idx) => (
                        <div key={idx} className="bg-black/30 p-2 rounded">
                          <span className="font-bold text-blue-400">
                            Page {src.page}:
                          </span>{" "}
                          <span className="text-gray-300">{src.text}...</span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="text-gray-400 animate-pulse">Thinking...</div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* INPUT */}
        <div className="p-4 border-t border-white/10 bg-[#212121]">
          <div className="max-w-3xl mx-auto flex gap-2">
            
            {/* FILE UPLOAD BUTTON */}
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFileUpload}
              accept=".pdf"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="bg-[#2f2f2f] px-4 rounded text-xl disabled:opacity-50 hover:bg-[#3f3f3f] transition-colors"
              disabled={uploading}
              title="Upload PDF"
            >
              {uploading ? "⏳" : "📎"}
            </button>

            <input
              className="flex-1 p-3 rounded bg-[#2f2f2f] outline-none"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />

            <button
              onClick={sendMessage}
              className="bg-white text-black px-4 rounded hover:bg-gray-200 transition-colors font-bold"
            >
              ↑
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}