/*jshint esversion: 6 */

const button = document.querySelector("#program");
const advanceButton = document.querySelector("#advance");
const div = document.querySelector("#output");
const periodsForm = document.querySelector("#periodsForm");
const periodsInput = document.querySelector("#new_periods");
const loginForm = document.querySelector("#loginForm");
const passwordInput = document.querySelector("#password");
const buttons = document.querySelector("#buttons");
const readout = document.querySelector("#readout");
const currentHeading = document.querySelector("#current-system");
const temperatureMap = {};
const INTERVAL_UPDATE = 5000;
const DEFAULT_USERNAME = "username"; // TODO: for sake of ease just hardcoded a username

let system_data;
let allSystems;
let interval;
let programOutput = "";
let temperatureOutput = "";
let currentTemperature;
let currentTarget;
let relayOn;
let t;

const withinOneSecond = (time) => {
  const currentTime = moment();
  return currentTime.diff(time, "seconds") === 1;
};

async function updateTemperatureMap() {
  if (!allSystems) {
    return;
  }
  if (withinOneSecond(temperatureMap.lastUpdated)) {
    return;
  }
  for (const system of allSystems) {
    const id = system.system_id;
    const temp = await getTemperature(id);
    temperatureMap[id] = temp;
  }
  temperatureMap.lastUpdated = moment();
}

async function setReadout() {
  if (!allSystems) return;
  if (Object.keys(temperatureMap).length === 0) await updateTemperatureMap();
  const elems = [];
  for (const system of allSystems) {
    const temp = temperatureMap[system.system_id];
    const str = `${system.system_id}: ${temp}˚C`;
    const elem = document.createElement("h3");
    elem.innerHTML = str;
    elems.push(elem);
  }
  readout.innerHTML = "";
  for (const elem of elems) {
    readout.appendChild(elem);
  }
}

const periodHelper =
  '<span class="period-helper"><br>[[startHour, endHour, targetTemp], ...]</span>';

function getSystems() {
  return fetch(`/api/v3/systems/`).then((response) =>
    response.json().then((data) => {
      if (response.status === 200) {
        programOutput = "";
        return sortData(data);
      } else {
        button.disabled = true;
        throw new Error(`${response.status}`);
      }
    })
  );
}

function toggleUIElements() {
  if (!t) {
    periodsForm.style.display = "none";
    button.style.display = "none";
    buttons.style.display = "none";
    button.style.display = "none";
    advanceButton.style.display = "none";
    currentHeading.innerText = "";
    return;
  }
  loginForm.style.display = "none";
  buttons.style.display = "block";

  if (!system_data) {
    button.style.display = "none";
    advanceButton.style.display = "none";
    periodsForm.style.display = "none";
    currentHeading.innerText = "";
    return;
  }
  button.style.display = "block";
  advanceButton.style.display = "block";
  if (system_data.advance) {
    advanceButton.style.fontWeight = "bold";
    advanceButton.disabled = true;
  } else {
    advanceButton.style.fontWeight = "normal";
    advanceButton.disabled = false;
  }
  currentHeading.innerText =
    system_data.system_id.substring(0, 1).toUpperCase() +
    system_data.system_id.substring(1);
  if (!system_data?.program) {
    periodsForm.style.display = "none";
  } else {
    periodsForm.style.display = "block";
  }
}

function setSystem(system_id) {
  programOutput = "";
  system_data = allSystems.find((system) => system.system_id === system_id);
  if (!system_data) {
    return;
  }
  toggleUIElements();
  update(system_data.system_id);
  const button1 = Array.from(buttons.children).find(
    (button) => button.innerHTML === system_data.system_id
  );
  const buttons2 = Array.from(buttons.children).filter(
    (button) => button.innerHTML !== system_data.system_id
  );
  button1.style.fontWeight = "bold";
  button1.style.boxShadow = "0 0 10px 2px rgba(255, 255, 255, 0.3)";
  buttons2.forEach((button) => {
    button.style.fontWeight = "normal";
    button1.style.boxShadow = "none";
  });
  button.innerHTML = system_data.program === false ? "ENABLE" : "DISABLE";
  button.disabled = false;
  periodsInput.value = system_data.program
    ? JSON.stringify(system_data.periods)
    : "";
  periodsInput.disabled = !system_data || !system_data.program;
  programOutput +=
    system_data.program === true ? "Program: ON" : "Program: OFF";
  if (system_data.program && system_data.periods) {
    if (system_data.periods.length > 0) {
      programOutput +=
        `<br><br>Periods: ${JSON.stringify(system_data.periods)}` +
        periodHelper;
    }
  }
  div.innerHTML = `${programOutput}${temperatureOutput}`;
  setTemperatureOutput();
}

function updatePeriod(event) {
  event.preventDefault();
  const systemId = system_data.system_id;
  if (!systemId) {
    return;
  }
  const method = "POST";
  const body = JSON.stringify({ periods: JSON.parse(periodsInput.value) });
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch(`/api/v3/periods/${systemId}/`, { method, headers, body }).then(
    function (response) {
      if (response.status !== 200) {
        localStorage.clear();
        throw new Error(response.detail);
      }
      response
        .json()
        .then(function (json) {
          system_data = json;
        })
        .then(() => {
          getSystems()
            .then((data) => (allSystems = data))
            .then(() => setSystem(system_data.system_id));
        });
    }
  );
}

function triggerAdvance() {
  const systemId = system_data.system_id;
  if (!systemId) {
    return;
  }
  const method = "POST";
  const body = JSON.stringify({ end_time: Date.now() / 1000 + 60 * 60 });
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch(`/api/v3/advance/${systemId}/`, { method, headers, body }).then(
    function (response) {
      if (response.status !== 200) {
        localStorage.clear();
        throw new Error(response.detail);
      }
      response.json().then(function (json) {
        system_data = json;
        toggleUIElements();
      });
    }
  );
}

function getTemperature(system) {
  return fetch(`/api/v3/temperature/${system}/`).then((response) =>
    response.json().then((data) => {
      if (response.status === 200) {
        temperatureOutput = "";
        return data.temperature;
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
  temperatureOutput = "";
  if (programOutput.length > 0) {
    temperatureOutput += "<br><br>";
  }
  temperatureOutput += `Temperature: ${JSON.stringify(
    temperatureMap[system_data.system_id]
  )}˚C ${!!currentTarget || relayOn ? "/" : ""} ${currentTarget || ""} ${
    relayOn ? "🔥" : ""
  }`;
  div.innerHTML = `${programOutput}${temperatureOutput}`;
}

function update(system) {
  updateTemperatureMap().then(() => {
    setReadout().then(() => {
      getTargetInfo(system).then((data) => {
        currentTarget = data.current_target;
        relayOn = data.relay_on;
        setTemperatureOutput();
      });
    });
  });
}

function onClick() {
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch("/api/v3/systems/", {
    method: "POST",
    headers,
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
    } else {
      localStorage.clear();
      window.location.reload();
    }
  });
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
  resetInterval();
}

function login(e) {
  e.preventDefault();
  const formData = new FormData();
  formData.set("username", DEFAULT_USERNAME);
  formData.set("password", passwordInput.value);

  fetch("/token/", {
    method: "POST",
    body: formData,
  }).then((result) =>
    result.json().then((data) => {
      if (result.status !== 200) {
        t = undefined;
        localStorage.clear();
        throw new Error(data.detail);
      }
      t = data;
      localStorage.setItem("t", JSON.stringify(t));
      if (t) {
        loginForm.style.display = "none";
      }
      toggleUIElements();
    })
  );
}

function sortData(data) {
  return data.sort((a, b) => {
    if (a.system_id < b.system_id) {
      return -1;
    }
    if (a.system_id > b.system_id) {
      return 1;
    }
    return 0;
  });
}

window.onload = () => {
  interval = setInterval(updateInterval, INTERVAL_UPDATE);
  periodsForm.addEventListener("submit", updatePeriod);
  loginForm.addEventListener("submit", login);
  periodsInput.disabled = !system_data;
  t = JSON.parse(localStorage.getItem("t") ?? "null");
  toggleUIElements();
  getSystems()
    .then((data) => (allSystems = data))
    .then(() => {
      for (const s of allSystems) {
        const button = document.createElement("button");
        button.innerHTML = s.system_id;
        button.addEventListener("click", (event) => idClickHandler(event, s));
        buttons.appendChild(button);
        buttons.style.display = "none";
      }
      setReadout().then(() => toggleUIElements());
    });
};
