import { useState, useRef, useEffect, useCallback } from "react";

function Functionalities() {
    const APP = "http://127.0.0.1:8000/";
    const POLL_INTERVAL_MS = 3000;

    const [isSidebarOpened, setIsSidebarOpened] = useState(false);
    const [humanQuery, setHumanQuery] = useState("");
    const [chatHistory, setChatHistory] = useState([]);
    const [file, setFile] = useState(null);
    const [networkError, setNetworkError] = useState(false);
    const fileInputRef = useRef(null);
    const chatEndRef = useRef(null);
    const attachmentUrlsRef = useRef(new Set());
    const pollTimersRef = useRef({}); 

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [chatHistory]);

    useEffect(() => {
        const urls = attachmentUrlsRef.current;
        return () => {
            urls.forEach((url) => URL.revokeObjectURL(url));
            urls.clear();
            
            Object.values(pollTimersRef.current).forEach(clearInterval);
        };
    }, []);

    const startPolling = useCallback((rowId, assistantMsgId) => {
        const timerId = setInterval(async () => {
            try {
                const res = await window.fetch(`${APP}manage_session/${rowId}/`);
                if (!res.ok) return;
                const data = await res.json();
                const response = data.model_response;

                if (response && response !== "Loading...") {
                    let displayText = response;
                    try { displayText = JSON.parse(response); } catch (_) {}
                    setChatHistory((prev) =>
                        prev.map((msg) =>
                            msg.id === assistantMsgId
                                ? { ...msg, text: displayText, loading: false }
                                : msg
                        )
                    );
                    clearInterval(timerId);
                    delete pollTimersRef.current[rowId];
                }
            } catch (e) {
                console.error("Polling error:", e);
            }
        }, POLL_INTERVAL_MS);

        pollTimersRef.current[rowId] = timerId;
    }, [APP]);

    function sendMessage() {
        const text = humanQuery.trim();
        if (!text && !file) return;
        const t = Date.now();
        const assistantMsgId = `a-${t}`;
        let attachment = null;
        if (file) {
            const url = URL.createObjectURL(file);
            attachmentUrlsRef.current.add(url);
            attachment = {
                name: file.name,
                url,
                isImage: file.type.startsWith("image/"),
            };
        }
        setChatHistory((prev) => [
            ...prev,
            { role: "user", text, id: `u-${t}`, attachment },
            { role: "assistant", text: "", id: assistantMsgId, loading: true },
        ]);
        send(text, file, assistantMsgId);
        setHumanQuery("");
        setFile(null);
    }

    function bubbleAriaLabel(msg) {
        if (msg.role !== "user") return `Insighter: ${msg.loading ? "Loading..." : msg.text}`;
        const parts = [];
        if (msg.attachment) parts.push(`file ${msg.attachment.name}`);
        if (msg.text) parts.push(msg.text);
        return parts.length ? `You: ${parts.join(". ")}` : "You";
    }

    function onAttachChange(e) {
        const f = e.target.files?.[0];
        if (f) setFile(f);
        e.target.value = "";
    }

    function clearSelectedFile() {
        setFile(null);
    }

    const sidebarClass = `sidebar ${isSidebarOpened ? "open" : "closed"}`;

    async function send(text, attachedFile, assistantMsgId) {
        const formdata = new FormData();
        formdata.append("human_query", text);
        if (attachedFile) {
            formdata.append("uploaded_file", attachedFile);
        }
        try {
            const response = await window.fetch(`${APP}create_session/`, {
                method: "POST",
                body: formdata,
            });
            const apistatus = await response.json();
            console.log("Session created:", apistatus);
            setNetworkError(false); // clear any previous network error

            const rowId = apistatus.id;
            if (rowId) {
                startPolling(rowId, assistantMsgId);
            }
        } catch (e) {
            console.error("Send error:", e);
            setNetworkError(true);
            setChatHistory((prev) =>
                prev.map((msg) =>
                    msg.id === assistantMsgId
                        ? { ...msg, text: "", loading: false, networkFail: true }
                        : msg
                )
            );
        }
    }

    return (
        <>
            <button type="button" className="toggle-btn" onClick={() => setIsSidebarOpened(!isSidebarOpened)}>
                ☰
            </button>
            <div className={sidebarClass}>
                <h2>Chat history</h2>
                <p>This feature is in development</p>
            </div>

            <h1 className="main" id="welcome" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <img
                    src="/back_icon.png"
                    alt="Back"
                    style={{ width: "80px", height: "60px", objectFit: "contain", cursor: "pointer", paddingLeft: "300px" }}
                    onClick={() => window.history.back()}
                    title="Go back"
                />
                ProdInsight
            </h1>

            <div id="chatArea" className="main" role="log" aria-live="polite" aria-relevant="additions">
                <div className="chat-messages">
                    {chatHistory.length === 0 ? (
                        <h3 className="chat-empty-hint">Welcome, Hope you are doing well</h3>
                    ) : (
                        chatHistory.map((msg) => (
                            <div
                                key={msg.id}
                                className={`chat-bubble chat-bubble-${msg.role}`}
                                aria-label={bubbleAriaLabel(msg)}
                            >
                                <span className="chat-bubble-label" aria-hidden="true" />
                                {msg.role === "user" && msg.attachment && (
                                    <div className="chat-bubble-attachment">
                                        {msg.attachment.isImage ? (
                                            <img
                                                src={msg.attachment.url}
                                                alt=""
                                                className="chat-bubble-attachment-image"
                                            />
                                        ) : (
                                            <div className="chat-bubble-file-placeholder" aria-hidden="true" />
                                        )}
                                        <span className="chat-bubble-file-name">{msg.attachment.name}</span>
                                    </div>
                                )}
                                {msg.role === "assistant" && msg.loading ? (
                                    <div className="chat-bubble-loading" aria-label="Insighter is generating response">
                                        <span className="loading-dot" />
                                        <span className="loading-dot" />
                                        <span className="loading-dot" />
                                    </div>
                                ) : msg.role === "assistant" && msg.networkFail ? (
                                    <p className="chat-network-error" role="alert">
                                        Unable to send message. Please check your network.
                                    </p>
                                ) : (
                                    msg.text ? <p className="chat-bubble-text">{msg.text}</p> : null
                                )}
                            </div>
                        ))
                    )}
                    <div ref={chatEndRef} className="chat-scroll-anchor" aria-hidden="true" />
                </div>
            </div>

            <div id="textbox" className="main">
                <div className="chat-input-bar">
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="chat-file-input-hidden"
                        aria-hidden="true"
                        tabIndex={-1}
                        onChange={onAttachChange}
                    />
                    <button
                        type="button"
                        className="chat-input-action chat-input-attach"
                        aria-label="Attach file"
                        title="Attach file"
                        onClick={() => fileInputRef.current?.click()}
                    />
                    {file ? (
                        <div className="chat-input-file-preview" title={file.name}>
                            <span className="chat-input-file-name">{file.name}</span>
                            <button
                                type="button"
                                className="chat-input-file-remove"
                                aria-label="Remove selected file"
                                title="Remove selected file"
                                onClick={clearSelectedFile}
                            >
                                ×
                            </button>
                        </div>
                    ) : null}
                    <input
                        type="text"
                        placeholder="Enter a product name to get its's insights"
                        id="chatInput"
                        value={humanQuery}
                        onChange={(e) => setHumanQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    />
                    <button
                        type="button"
                        className="chat-input-action chat-input-send"
                        aria-label="Send message"
                        title="Send message"
                        onClick={sendMessage}
                    />
                </div>
            </div>
        </>
    );
}

export default Functionalities;
