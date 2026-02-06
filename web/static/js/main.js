const logsEl = document.getElementById("logs");
const btnRun = document.getElementById("btnRun");
const btnDownload = document.getElementById("btnDownload");

const statusBadge = document.getElementById("statusBadge");
const lastRun = document.getElementById("lastRun");
const lastPdf = document.getElementById("lastPdf");
const exitCode = document.getElementById("exitCode");
const stopBtn = document.getElementById("stopBtn");

stopBtn.addEventListener("click", async () => {
  const confirmStop = confirm("¿Seguro que quieres detener el proceso?");
  if (!confirmStop) return;

  stopBtn.disabled = true;

  try {
    const res = await fetch("/api/stop", { method: "POST" });
    const data = await res.json();

    if (!data.ok) {
      alert(data.message || "No se pudo detener.");
      return;
    }

    alert("Proceso detenido.");
  } catch (err) {
    alert("Error: " + err);
  }
});

async function fetchStatus(){
  const r = await fetch("/api/status");
  return await r.json();
}

async function fetchLogs(){
  const r = await fetch("/api/logs");
  const data = await r.json();
  return data.logs || "";
}

function setStatusUI(state){
  lastRun.textContent = state.last_run || "—";
  lastPdf.textContent = state.last_pdf || "—";
  exitCode.textContent = (state.exit_code === null || state.exit_code === undefined) ? "—" : state.exit_code;

  if(state.running){
    statusBadge.textContent = "En ejecución";
    statusBadge.style.color = "#f1c40f";
    btnRun.disabled = true;
  } else {
    btnRun.disabled = false;

    if(state.exit_code === 0){
      statusBadge.textContent = "Terminado";
      statusBadge.style.color = "#2ecc71";
    } else if(state.exit_code !== null){
      statusBadge.textContent = "Error";
      statusBadge.style.color = "#ff4d4d";
    } else {
      statusBadge.textContent = "Listo";
      statusBadge.style.color = "rgba(233,238,252,0.65)";
    }
  }

  // Link descarga
  if(state.last_pdf){
    btnDownload.href = "/api/download";
    btnDownload.style.opacity = "1";
    btnDownload.style.pointerEvents = "auto";
  } else {
    btnDownload.href = "#";
    btnDownload.style.opacity = "0.5";
    btnDownload.style.pointerEvents = "none";
  }
}

async function refresh(){
  try{
    const [state, logs] = await Promise.all([fetchStatus(), fetchLogs()]);
    setStatusUI(state);

    const oldScroll = logsEl.scrollTop;
    const atBottom = (logsEl.scrollHeight - logsEl.clientHeight - logsEl.scrollTop) < 60;

    logsEl.textContent = logs || "(sin logs aún)";

    if(atBottom){
      logsEl.scrollTop = logsEl.scrollHeight;
    } else {
      logsEl.scrollTop = oldScroll;
    }

    if (state.running) {
  btnRun.disabled = true;
  stopBtn.disabled = false;
    } else {
  btnRun.disabled = false;
  stopBtn.disabled = true;
} 

  } catch(e){
    logsEl.textContent = "Error cargando logs: " + e;
  }
}

async function runMotor(){
  btnRun.disabled = true;
  try{
    const r = await fetch("/api/run", { method: "POST" });
    const data = await r.json();
    if(!data.ok){
      alert(data.message || "No se pudo iniciar");
    }
  } catch(e){
    alert("Error: " + e);
  }
}

async function openFolder(which){
  try{
    const r = await fetch("/api/open-folder", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ which })
    });
    const data = await r.json();
    if(!data.ok){
      alert(data.message || "No se pudo abrir la carpeta");
    }
  } catch(e){
    alert("Error: " + e);
  }
}

btnRun.addEventListener("click", runMotor);

// refresco automático
refresh();
setInterval(refresh, 1200);

// Exponer para botones HTML
window.openFolder = openFolder;
