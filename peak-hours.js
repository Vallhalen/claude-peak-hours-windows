/**
 * Peak hours logic — shared between page and service worker.
 * Peak: weekdays 5:00–11:00 AM Pacific Time.
 * Zero API calls — pure clock math.
 */

const PEAK_START_HOUR = 5;
const PEAK_END_HOUR = 11;
const WARNING_SECONDS = 15 * 60;

function getPeakState() {
    const now = new Date();

    // Get current time in Pacific Time
    const ptString = now.toLocaleString('en-US', { timeZone: 'America/Los_Angeles' });
    const pt = new Date(ptString);
    const weekday = pt.getDay(); // 0=Sun, 6=Sat
    const hour = pt.getHours();
    const minute = pt.getMinutes();
    const second = pt.getSeconds();

    const isWeekday = weekday >= 1 && weekday <= 5;
    const isPeak = isWeekday && hour >= PEAK_START_HOUR && hour < PEAK_END_HOUR;

    const secondsIntoDay = hour * 3600 + minute * 60 + second;
    const peakStartSec = PEAK_START_HOUR * 3600;
    const peakEndSec = PEAK_END_HOUR * 3600;

    let secsUntilChange;
    let nextIsPeak;

    if (!isWeekday) {
        // Weekend → next Monday 5:00 AM PT
        const daysUntilMonday = weekday === 0 ? 1 : (8 - weekday);
        secsUntilChange = daysUntilMonday * 86400 - secondsIntoDay + peakStartSec;
        nextIsPeak = true;
    } else if (isPeak) {
        secsUntilChange = peakEndSec - secondsIntoDay;
        nextIsPeak = false;
    } else if (secondsIntoDay < peakStartSec) {
        secsUntilChange = peakStartSec - secondsIntoDay;
        nextIsPeak = true;
    } else {
        // After peak today
        if (weekday === 5) { // Friday after peak → Monday
            secsUntilChange = 2 * 86400 + (86400 - secondsIntoDay) + peakStartSec;
        } else {
            secsUntilChange = (86400 - secondsIntoDay) + peakStartSec;
        }
        nextIsPeak = true;
    }

    secsUntilChange = Math.max(0, secsUntilChange);

    let status;
    if (secsUntilChange <= WARNING_SECONDS) {
        status = 'warning';
    } else if (isPeak) {
        status = 'peak';
    } else {
        status = 'off-peak';
    }

    // Local peak hours string
    const today = new Date();
    const startUTC = new Date(today.toLocaleDateString('en-CA', { timeZone: 'America/Los_Angeles' }) + 'T05:00:00-08:00');
    const endUTC = new Date(today.toLocaleDateString('en-CA', { timeZone: 'America/Los_Angeles' }) + 'T11:00:00-08:00');

    // Recalculate properly using PT offset
    const ptNow = new Date(now.toLocaleString('en-US', { timeZone: 'America/Los_Angeles' }));
    const ptOffset = now.getTime() - ptNow.getTime();
    const localStart = new Date(new Date(today.getFullYear(), today.getMonth(), today.getDate(), PEAK_START_HOUR, 0, 0).getTime() + ptOffset);
    const localEnd = new Date(new Date(today.getFullYear(), today.getMonth(), today.getDate(), PEAK_END_HOUR, 0, 0).getTime() + ptOffset);

    const fmt = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    const tzAbbr = Intl.DateTimeFormat([], { timeZoneName: 'short' }).formatToParts(now)
        .find(p => p.type === 'timeZoneName')?.value || 'local';

    const peakHoursLocal = `${fmt(localStart)}\u2013${fmt(localEnd)} ${tzAbbr}`;

    return {
        isPeak,
        status,
        secondsUntilChange: secsUntilChange,
        countdownText: formatCountdown(secsUntilChange),
        peakHoursLocal,
        nextIsPeak,
        emoji: status === 'off-peak' ? '🟢' : status === 'peak' ? '🔴' : '🟡',
    };
}

function formatCountdown(seconds) {
    const totalMinutes = Math.floor(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours > 24) {
        const days = Math.floor(hours / 24);
        const remainingHours = hours % 24;
        return `${days}d ${remainingHours}h`;
    }
    if (hours > 0) {
        return `${hours}h ${minutes}min`;
    }
    return `${minutes}min`;
}

// Export for service worker (if module) or global scope
if (typeof module !== 'undefined') {
    module.exports = { getPeakState, formatCountdown };
}
