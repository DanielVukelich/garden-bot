function refreshCam() {
    var cam = document.getElementById('video-feed');
    cam.src = '/camera?ms=' + 5000 + '&t=' + Date.now();
}

if(document.getElementById('video-feed') != null) {
    refreshCam();
    setInterval(refreshCam, 5000);
}

function refreshStatus() {
    var request = new XMLHttpRequest();
    request.open('GET', '/api/solenoid');
    request.send();

    request.onload = async function () {
        var data = JSON.parse(this.response);
        document.getElementById('status').value = this.response
    }
}
refreshStatus();
setInterval(refreshStatus, 1000);

function TriggerSolenoid() {
    id = document.querySelector('input[name="select_solenoid"]:checked').value;

    var request = new XMLHttpRequest();
    request.open('POST', '/api/solenoid?id=' + id);
    request.send();

    request.onload = async function () {
        var data = JSON.parse(this.response);
        if(data.queued)
            document.getElementById('job-result').innerHTML = 'Result: Successfully queued';
        else
            document.getElementById('job-result').innerHTML = 'Result: Another job is already running';
    }
}


last_flow_sample = null
function refreshFlow() {
    var request = new XMLHttpRequest();
    if(last_flow_sample === null)
        path = '/api/flow'
    else
        path = '/api/flow?from=' + last_flow_sample.toISOString();
    request.open('GET', path);
    request.send();

    request.onload = async function () {
        var data = JSON.parse(this.response);
        document.getElementById('flow').value = this.response;
        if(data.timestamp === null)
            return;
        last_flow_sample = new Date(data.timestamp);
    }
}

refreshFlow();
refreshStatus();
setInterval(refreshFlow, 500);

flow_rate = null

function SimulateWaterFlow() {
    allow_pin_mock_panel = document.getElementById('pin-mock');
    if(allow_pin_mock_panel === null)
        return;

    if(flow_rate != null){
        clearInterval(flow_rate)
        flow_rate = null
    }

    hz = document.querySelector('input[name="simulate-hz"]').value;
    if(hz === "0")
        return

    interval = 1000 / hz
    if(interval < 1/120)
        return

    function fire_req() {
        var request = new XMLHttpRequest();
        request.open('POST', '/api/flow');
        request.send();
    }

    flow_rate = setInterval(fire_req, interval)
}

function StopWaterFlow() {
    if(flow_rate === null)
        return;
    clearInterval(flow_rate)
}
