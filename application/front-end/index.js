/*jshint esversion: 6 */

let system_data;
let allSystems;
let button = document.querySelector("#program");
let div = document.querySelector("#output");
let periodsForm = document.querySelector("#periodsForm");
let periodsInput = document.querySelector("#new_periods");
let interval;
let INTERVAL_UPDATE = 15000;
let programOutput = "";
let temperatureOutput = "";
let currentTemperature;
let currentTarget;
let relayOn;
const buttons = document.getElementById("buttons");


const periodHelper =
    '<span class="period-helper"><br>[[startHour, endHour, targetTemp], ...]</span>';

function getSystems() {
    return fetch(`/api/v3/systems/`).then((response) =>
        response.json().then((data) => {
            if (response.status === 200) {
                programOutput = "";
                return data;
            } else {
                button.disabled = true;
                throw new Error(`${response.status}`);
            }
        })
    );
}

function setSystem(system_id) {
    programOutput = "";
    system_data = allSystems.find(system => system.system_id === system_id);
    if (!system_data) {
        button.disabled = true;
        return;
    }
    const button1 = Array.from(buttons.children).find(button => button.innerHTML === system_data.system_id);
    const buttons2 = Array.from(buttons.children).filter(button => button.innerHTML !== system_data.system_id);
    button1.style.fontWeight = "bold";
    button1.style.boxShadow = "0 0 10px 2px rgba(255, 255, 255, 0.3)";
    buttons2.forEach(button => {
        button.style.fontWeight = "normal";
        button1.style.boxShadow = "none";
    });
    button.innerHTML = system_data.program === false ? "ENABLE" : "DISABLE";
    button.disabled = false;
    periodsInput.value = system_data.program ? JSON.stringify(system_data.periods) : "";
    periodsInput.disabled = !system_data || !system_data.program;
    programOutput += system_data.program === true ? "Program: ON" : "Program: OFF";
    if (system_data.program && system_data.periods) {
        if (system_data.periods.length > 0) {
            programOutput +=
                `<br><br>Periods: ${JSON.stringify(system_data.periods)}` + periodHelper;
        }
    }
    div.innerHTML = `${programOutput}${temperatureOutput}`;
}

function updatePeriod(event) {
    event.preventDefault();
    const systemId = system_data.system_id;
    if (!systemId) {
        return;
    }
    const method = 'POST';
    const body = JSON.stringify({periods: JSON.parse(periodsInput.value)});
    const headers = new Headers({'Content-Type': 'application/json'});
    fetch(`/api/v3/periods/${systemId}/`, {method, headers, body}).then(function (response) {
        if (response.status !== 200) {
            throw new Error(response.detail);
        }
        response.json().then(function (json) {
            system_data = json;
        }).then(() => {
            getSystems().then(data => allSystems = data).then(() => setSystem(system_data.system_id));
        });
    });
}

function getTemperature(system) {
    return fetch(`/api/v3/temperature/${system}/`).then((response) =>
        response.json().then((data) => {
            if (response.status === 200) {
                temperatureOutput = "";
                return data;
            }
            button.disabled = true;
            throw new Error(`${response.status}`);
        })
    );
}

function getTargetInfo(system) {
    return fetch(`/api/v3/target/${system}/`).then((response) =>
        response.json().then((data) => {
            if (response.status === 200) {
                temperatureOutput = "";
                return data;
            }
            button.disabled = true;
            throw new Error(`${response.status}`);
        })
    );
}

function setTemperatureOutput() {
    if (programOutput.length > 0) {
        temperatureOutput += "<br><br>";
    }
    temperatureOutput += `Temperature: ${JSON.stringify(currentTemperature)}˚C ${!!currentTarget || relayOn ? "/" : ""} ${currentTarget || ""} ${relayOn ? "🔥" : ""}`;
    div.innerHTML = `${programOutput}${temperatureOutput}`;
}

function update(system) {
    getTargetInfo(system).then((data) => {
        currentTarget = data.current_target;
        relayOn = data.relay_on;
        setTemperatureOutput();
    });
    getTemperature(system).then((data) => {
        currentTemperature = data;
        setTemperatureOutput();
    });
}

function onClick() {
    fetch("/api/v3/systems/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            system_id: system_data.system_id,
            program: !system_data.program,
        }),
    }).then((response) => {
            if (response.status === 200) {
                getSystems().then((data) => {
                    allSystems = data;
                    setSystem(system_data.system_id);
                });
                updateInterval();
                resetInterval();
            }
        }
    );
}

function updateInterval() {
    if (!system_data) {
        return;
    }
    update(system_data.system_id);
}

function resetInterval() {
    clearInterval(interval);
    interval = setInterval(updateInterval, INTERVAL_UPDATE);
}

function idClickHandler(event, s) {
    setSystem(s.system_id);
    updateInterval();
    resetInterval();
}

window.onload = () => {
    button.disabled = true;
    interval = setInterval(updateInterval, INTERVAL_UPDATE);
    periodsForm.addEventListener("submit", updatePeriod);
    periodsInput.disabled = !system_data;
    getSystems().then(data => allSystems = data).then(() => {
        for (const s of allSystems) {
            const button = document.createElement("button");
            button.innerHTML = s.system_id;
            button.addEventListener("click", (event) => idClickHandler(event, s));
            buttons.appendChild(button);
        }
    });
};
