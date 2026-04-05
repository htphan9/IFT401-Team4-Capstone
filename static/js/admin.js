// If one time field is filled, require the other one too
var startTime = document.getElementById('startTime');
var endTime = document.getElementById('endTime');

function syncRequired() {
    if (startTime.value || endTime.value) {
        startTime.required = true;
        endTime.required = true;
    } else {
        startTime.required = false;
        endTime.required = false;
    }
}

startTime.addEventListener('input', syncRequired);
endTime.addEventListener('input', syncRequired);