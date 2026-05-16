import { useState, useEffect } from "react";

function Functionalities2(){
    const backend="http://127.0.0.1:8000/"

    const [isSidebarOpen, openSidebar]=useState(false);
    const [humanMessage, setHumanMessage]=useState("");
    const [aimessage, setAiMessage]=useState("");

    async function fetch_url(){
        await fetch()
    }

    return(
        <>
        <button className="toggle-btn" onClick={openSidebar(!isSidebarOpen)}>☰</button>
        <div id="sidebar"></div>
        </>
    );
}

export default Functionalities2;