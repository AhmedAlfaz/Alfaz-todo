#!/usr/bin/env python3
"""Time-logic tests for ABDO: recurrence, reminders, prayer-time timezone.

Why this file exists: the Phase 3 review found that `planMatchesDate()` silently produced no
occurrence for a monthly plan on the 31st in 5 of 12 months, and none for a Feb-29 yearly plan in
3 of 4 years - and there was no harness that would have caught it. This is that harness. It runs
against the *shipped* functions extracted straight out of index.html, not a copy, so it cannot
drift.

  python3 tools/test_planner_time.py          # run everything
  python3 tools/test_planner_time.py --check  # same, quieter (for gates/CI)

Requires node (the repo already needs it for tools/gates.py). No npm packages.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, 'index.html')

FAIL = []
NOTE = []


def fail(msg):
    FAIL.append(msg)


def read_index():
    with open(HTML, encoding='utf-8') as f:
        return f.read()


def extract_block(src, start_marker, end_marker):
    """Return the source text between two markers, raising loudly if either is missing."""
    i = src.find(start_marker)
    if i < 0:
        raise SystemExit(f'extract_block: {start_marker!r} not found in index.html')
    j = src.find(end_marker, i)
    if j < 0:
        raise SystemExit(f'extract_block: {end_marker!r} not found after {start_marker!r}')
    return src[i:j]


def run_node(script, tz='Africa/Cairo'):
    """Execute a JS snippet with node in a fixed timezone. Returns (ok, stdout, stderr)."""
    fd, path = tempfile.mkstemp(suffix='.js', prefix='abdo-time-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(script)
        env = dict(os.environ, TZ=tz)
        r = subprocess.run(['node', path], capture_output=True, text=True, env=env, timeout=120)
        return r.returncode == 0, r.stdout, r.stderr
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# --------------------------------------------------------------------------------------------------
# The harness body. Each case prints "ok" or "FAIL <name>", so python can own the reporting.
# --------------------------------------------------------------------------------------------------
HARNESS_PRELUDE = r"""
const results = [];
function ok(name, cond, detail) { results.push({ name, pass: !!cond, detail: detail === undefined ? '' : String(detail) }); }
function eqDay(iso) { const [y, m, d] = iso.split('-').map(Number); return Date.UTC(y, m - 1, d) / 86400000; }
"""

# --- 1. recurrence ------------------------------------------------------------------------------
RECURRENCE_CASES = r"""
// ---- monthly on the 31st must not vanish in short months ----
const m31 = { id: 'm31', title: 'Rent', date: '2026-01-31', time: '', note: '', repeat: 'monthly', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-02-28', true], ['2026-04-30', true], ['2026-06-30', true], ['2026-09-30', true], ['2026-11-30', true],
 ['2026-03-31', true], ['2026-05-31', true], ['2026-03-30', false], ['2026-02-27', false], ['2026-02-30', false]]
.forEach(([iso, want]) => ok('monthly-31st ' + iso + ' expected ' + (want ? 'shown' : 'absent'),
  planMatchesDate(m31, iso) === want, 'got ' + planMatchesDate(m31, iso)));

// ---- monthly on the 30th: February must clamp, not skip ----
const m30 = { id: 'm30', title: 'Bill', date: '2026-01-30', time: '', note: '', repeat: 'monthly', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-02-28', true], ['2026-03-30', true], ['2026-04-30', true], ['2026-03-29', false]]
.forEach(([iso, want]) => ok('monthly-30th ' + iso + ' expected ' + (want ? 'shown' : 'absent'),
  planMatchesDate(m30, iso) === want, 'got ' + planMatchesDate(m30, iso)));

// ---- every-N-months from the 31st keeps clamping, and interval is respected ----
const m31x2 = { id: 'm31x2', title: 'Quarterly', date: '2026-01-31', time: '', note: '', repeat: 'monthly', repeat_interval: 2, repeat_until: '', status: '', created: 0 };
[['2026-03-31', true], ['2026-05-31', true], ['2026-02-28', false], ['2026-04-30', false], ['2026-07-31', true]]
.forEach(([iso, want]) => ok('monthly-2x-31st ' + iso, planMatchesDate(m31x2, iso) === want, 'got ' + planMatchesDate(m31x2, iso)));

// ---- yearly on Feb 29: clamp to Feb 28 in common years ----
const feb29 = { id: 'f29', title: 'Anniversary', date: '2024-02-29', time: '', note: '', repeat: 'yearly', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2025-02-28', true], ['2026-02-28', true], ['2027-02-28', true], ['2028-02-29', true],
 ['2025-03-01', false], ['2026-02-27', false]]
.forEach(([iso, want]) => ok('yearly-Feb29 ' + iso, planMatchesDate(feb29, iso) === want, 'got ' + planMatchesDate(feb29, iso)));

// ---- yearly every 2 years from Feb 29 ----
const feb29x2 = { id: 'f29x2', title: 'Biennial', date: '2024-02-29', time: '', note: '', repeat: 'yearly', repeat_interval: 2, repeat_until: '', status: '', created: 0 };
[['2026-02-28', true], ['2028-02-29', true], ['2025-02-28', false], ['2027-02-28', false]]
.forEach(([iso, want]) => ok('yearly-2x-Feb29 ' + iso, planMatchesDate(feb29x2, iso) === want, 'got ' + planMatchesDate(feb29x2, iso)));

// ---- regression guard: everything that already worked must still work ----
const daily = { id: 'd', title: 'Daily', date: '2026-01-31', time: '', note: '', repeat: 'daily', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-01-31', true], ['2026-02-01', true], ['2026-12-31', true], ['2026-01-30', false]]
.forEach(([iso, want]) => ok('daily ' + iso, planMatchesDate(daily, iso) === want, 'got ' + planMatchesDate(daily, iso)));

const daily2 = { id: 'd2', title: 'Every 2', date: '2026-04-20', time: '', note: '', repeat: 'daily', repeat_interval: 2, repeat_until: '', status: '', created: 0 };
[['2026-04-22', true], ['2026-04-24', true], ['2026-04-23', false], ['2026-04-30', true]]
.forEach(([iso, want]) => ok('daily-2 ' + iso, planMatchesDate(daily2, iso) === want, 'got ' + planMatchesDate(daily2, iso)));

const weekly = { id: 'w', title: 'Weekly', date: '2026-04-18', time: '', note: '', repeat: 'weekly', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-04-25', true], ['2026-10-31', true], ['2026-11-01', false], ['2026-04-19', false]]
.forEach(([iso, want]) => ok('weekly ' + iso, planMatchesDate(weekly, iso) === want, 'got ' + planMatchesDate(weekly, iso)));

const weekly2 = { id: 'w2', title: 'Fortnightly', date: '2026-04-18', time: '', note: '', repeat: 'weekly', repeat_interval: 2, repeat_until: '', status: '', created: 0 };
[['2026-05-02', true], ['2026-05-09', false], ['2026-05-16', true]]
.forEach(([iso, want]) => ok('weekly-2 ' + iso, planMatchesDate(weekly2, iso) === want, 'got ' + planMatchesDate(weekly2, iso)));

const once = { id: 'o', title: 'Once', date: '2026-06-01', time: '', note: '', repeat: 'none', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-06-01', true], ['2026-06-02', false]]
.forEach(([iso, want]) => ok('one-off ' + iso, planMatchesDate(once, iso) === want, 'got ' + planMatchesDate(once, iso)));

// ---- repeat_until is an inclusive day ----
const until = { id: 'u', title: 'Until', date: '2026-01-01', time: '', note: '', repeat: 'daily', repeat_interval: 1, repeat_until: '2026-01-05', status: '', created: 0 };
[['2026-01-05', true], ['2026-01-06', false]]
.forEach(([iso, want]) => ok('until ' + iso, planMatchesDate(until, iso) === want, 'got ' + planMatchesDate(until, iso)));

// ---- DST transitions must not shift a daily plan ----
const dstDaily = { id: 'dst', title: 'DST', date: '2026-04-20', time: '', note: '', repeat: 'daily', repeat_interval: 1, repeat_until: '', status: '', created: 0 };
[['2026-04-24', true], ['2026-04-25', true], ['2026-10-29', true], ['2026-10-30', true]]
.forEach(([iso, want]) => ok('dst-daily ' + iso, planMatchesDate(dstDaily, iso) === want, 'got ' + planMatchesDate(dstDaily, iso)));

// ---- next occurrence search terminates and is correct (used by the recurrence fix) ----
if (typeof nextPlanOccurrence === 'function') {
  const n1 = nextPlanOccurrence(m31, '2026-02-01', 60);
  ok('nextPlanOccurrence monthly-31 from Feb 1 -> Feb 28', n1 === '2026-02-28', n1);
  const n2 = nextPlanOccurrence(m31, '2026-03-01', 60);
  ok('nextPlanOccurrence monthly-31 from Mar 1 -> Mar 31', n2 === '2026-03-31', n2);
  const n3 = nextPlanOccurrence(feb29, '2026-01-01', 800);
  ok('nextPlanOccurrence yearly-Feb29 from Jan 2026 -> Feb 28', n3 === '2026-02-28', n3);
  const n4 = nextPlanOccurrence(until, '2026-01-03', 60);
  ok('nextPlanOccurrence respects repeat_until', n4 === '2026-01-03', n4);
  const n4b = nextPlanOccurrence(until, '2026-01-06', 60);
  ok('nextPlanOccurrence returns null once repeat_until has passed', n4b === null, n4b);
  const n5 = nextPlanOccurrence({ id: 'x', date: '2026-01-01', repeat: 'none', repeat_interval: 1, repeat_until: '', status: '', created: 0 }, '2026-01-02', 60);
  ok('nextPlanOccurrence one-off in the past is null', n5 === null, n5);
}
"""

# --- 2. reminder window -------------------------------------------------------------------------
REMINDER_CASES = r"""
// The alarm must fire once, when it is due, and not for an hour afterwards.
const mk = (o) => Object.assign({ id: 't1', text: 'Task', done: false, status: 'pending', due_date: '2026-11-21', due_time: '09:00', reminder_minutes: 15, reminder_fired: false }, o);
function fireAt(task, hhmm, nowIso) {
  return reminderShouldFire(task, nowIso || ('2026-11-21T' + hhmm + ':00'), nowIso === 'next-day' ? '2026-11-22T00:05:00' : null);
}
ok('reminder 15m before 09:00 does NOT fire at 08:44', reminderShouldFire(mk({}), '2026-11-21T08:44:00') === false);
ok('reminder 15m before 09:00 fires at 08:45', reminderShouldFire(mk({}), '2026-11-21T08:45:00') === true);
ok('reminder 15m before 09:00 fires at 08:46 (catch-up)', reminderShouldFire(mk({}), '2026-11-21T08:46:00') === true);
ok('reminder 15m before 09:00 does NOT fire at 09:30', reminderShouldFire(mk({}), '2026-11-21T09:30:00') === false);
ok('due-now task fires at 09:00', reminderShouldFire(mk({ reminder_minutes: 0 }), '2026-11-21T09:00:00') === true);
ok('due-now task does NOT fire at 09:41', reminderShouldFire(mk({ reminder_minutes: 0 }), '2026-11-21T09:41:00') === false);
ok('already-fired task never fires again', reminderShouldFire(mk({ reminder_fired: true }), '2026-11-21T08:45:00') === false);
ok('done task never fires', reminderShouldFire(mk({ done: true }), '2026-11-21T08:45:00') === false);
ok('cancelled task never fires', reminderShouldFire(mk({ status: 'cancelled' }), '2026-11-21T08:45:00') === false);
ok('task without a time never fires', reminderShouldFire(mk({ due_time: null }), '2026-11-21T09:00:00') === false);

// The 23:45 case: fire time 23:45, checked at 00:05 the next day.
const late = mk({ due_time: '23:45', reminder_minutes: 0 });
ok('23:45 task fires at 23:45', reminderShouldFire(late, '2026-11-21T23:45:00') === true);
ok('23:45 task still fires at 00:05 via its catch-up window', reminderShouldFire(late, '2026-11-22T00:05:00') === true);
const lateRem = mk({ due_time: '23:50', reminder_minutes: 15 });   // fire time 23:35
ok('23:50/15min task fires at 23:35', reminderShouldFire(lateRem, '2026-11-21T23:35:00') === true);
ok('23:50/15min task fires at 00:05 via catch-up', reminderShouldFire(lateRem, '2026-11-22T00:05:00') === true);
ok('yesterday catch-up older than 90min is dropped', reminderShouldFire(late, '2026-11-21T02:00:00') === false);

// ---- snooze must not move the task's own due time ----
const snoozed = mk({ reminder_minutes: 0 });
const until = snoozeUntil(snoozed, 15, '2026-11-21T09:00:00');
ok('snoozeUntil(09:00 +15) = 09:15', until === '2026-11-21T09:15', until);
const snoozedLate = snoozeUntil(mk({ due_time: '23:50', reminder_minutes: 0 }), 15, '2026-11-21T23:50:00');
ok('snooze across midnight rolls the date', snoozedLate === '2026-11-22T00:05', snoozedLate);
const task2 = { due_time: '09:00', due_date: '2026-11-21', snooze_until: '2026-11-21T09:15' };
ok('snoozed task does not fire at its original 09:00', reminderShouldFire(Object.assign(mk({}), { snooze_until: '2026-11-21T09:15' }), '2026-11-21T09:00:00') === false);
ok('snoozed task fires at the snooze time', reminderShouldFire(Object.assign(mk({}), { snooze_until: '2026-11-21T09:15' }), '2026-11-21T09:15:00') === true);
ok('snoozed task does not fire after the snooze window', reminderShouldFire(Object.assign(mk({}), { snooze_until: '2026-11-21T09:15' }), '2026-11-21T09:50:00') === false);
"""

# --- 3. prayer-time timezone --------------------------------------------------------------------
PLAN_DONE_CASES = r"""
// ---- per-occurrence completion for repeating plans ----
const rep = { id: 'r1', title: 'Daily walk', date: '2026-11-20', time: '', note: '', repeat: 'daily', repeat_interval: 1, repeat_until: '', status: '', done_dates: { '2026-11-21': 1 }, created: 0 };
ok('repeating plan: today marked done', planDoneOn(rep, '2026-11-21') === true);
ok('repeating plan: yesterday not marked done', planDoneOn(rep, '2026-11-20') === false);
ok('repeating plan: tomorrow not done', planDoneOn(rep, '2026-11-22') === false);
const oneOff = { id: 'o1', title: 'Once', date: '2026-11-21', time: '', note: '', repeat: 'none', status: 'done', created: 0 };
ok('one-off plan uses status', planDoneOn(oneOff, '2026-11-21') === true);
ok('a repeating plan still shows on later days (no monthly-skip regression)', planMatchesDate(rep, '2026-12-01') === true);
"""


TZ_CASES = r"""
// Aladhan returns wall-clock times for the coordinates' zone (timezone is derived from latitude /
// longitude unless passed). The app stored them keyed by date only, with no zone, and compared them
// to the device clock. prayerZoneOffsetMinutes() must derive the offset from the API payload.
const payload = {
  data: {
    timings: { Fajr: '05:12', Dhuhr: '12:30', Asr: '15:40', Maghrib: '18:12', Isha: '19:30' },
    meta: { timezone: 'Europe/London', latitude: 51.5074, longitude: -0.1278, method: { id: 5 } }
  }
};
const stored = prayerTimesToStore(payload, '2026-11-21');   // ISO date, v3 cache
ok('stored payload keeps the zone name', stored && stored.timezone === 'Europe/London', stored && stored.timezone);
ok('stored payload keeps the coordinates', stored && stored.lat === 51.5074 && stored.lng === -0.1278, stored && (stored.lat + ',' + stored.lng));
ok('stored payload keeps the timings', stored && stored.timings && stored.timings.Maghrib === '18:12', stored && stored.timings && stored.timings.Maghrib);

const off = prayerZoneOffsetMinutes(stored, '2026-11-21');
ok('offset for Europe/London on 2026-11-21 is 0', off === 0, off);
// A real v2 cache wrote DD-MM-YYYY; it must still resolve to the same zone offset.
const v2stored = { v: 2, date_key: '21-11-2026', timezone: 'Europe/London', timings: payload.data.timings };
ok('v2 DD-MM-YYYY date key resolves the same offset', prayerZoneOffsetMinutes(v2stored, '21-11-2026') === 0, prayerZoneOffsetMinutes(v2stored, '21-11-2026'));

// A device in Cairo reading London times must correct by the difference (Cairo is UTC+2 in Nov).
const deviceOff = -new Date('2026-11-21T12:00:00').getTimezoneOffset();  // 120 in Africa/Cairo
ok('device offset in Africa/Cairo is +120', deviceOff === 120, deviceOff);
const shifted = prayerTimesInDeviceClock(stored, '2026-11-21');
ok('London 18:12 appears at 20:12 on a Cairo device', shifted && shifted.Maghrib === '20:12', shifted && shifted.Maghrib);
ok('London 05:12 appears at 07:12 on a Cairo device', shifted && shifted.Fajr === '07:12', shifted && shifted.Fajr);

// Same zone: nothing shifts.
const sameZone = prayerTimesToStore({ data: { timings: payload.data.timings, meta: { timezone: 'Africa/Cairo', latitude: 27.26, longitude: 33.81 } } }, '2026-11-21');
const unshifted = prayerTimesInDeviceClock(sameZone, '2026-11-21');
ok('same-zone times are unchanged', unshifted && unshifted.Maghrib === '18:12', unshifted && unshifted.Maghrib);

// Legacy cache entries (bare timings, v1) and v2 entries with no zone must not crash and must pass through.
ok('legacy bare timings pass through unchanged', (prayerTimesInDeviceClock({ Fajr: '05:00' }, '2026-11-21') || {}).Fajr === '05:00');
ok('v2 cache without a zone passes through unchanged', (prayerTimesInDeviceClock({ v: 2, timings: { Fajr: '05:00' } }, '2026-11-21') || {}).Fajr === '05:00');
"""


def build_script(src, cases):
    # isoToDay/dayParts/daysInMonth live just above planMatchesDate (they are its helpers), so the
    # slice starts at isoToDay, not at planMatchesDate.
    recurrence = extract_block(src, 'function isoToDay', 'function plansForIso')
    reminder = (extract_block(src, 'function parseIsoLocal', 'function checkTaskReminders')
                if src.find('function parseIsoLocal') < src.find('const REMINDER_CATCHUP_MIN')
                else extract_block(src, 'const REMINDER_CATCHUP_MIN', 'function checkTaskReminders'))
    tz = extract_block(src, 'function prayerTimesToStore', 'function fetchPrayerTimes')
    planner_done = extract_block(src, 'function togglePlanDone', 'let editingPlanId')
    return '\n'.join([
        HARNESS_PRELUDE,
        recurrence,
        reminder,
        tz,
        planner_done,
        cases,
        'console.log(JSON.stringify(results));',
    ])


def run_suite(name, cases, src, tz='Africa/Cairo'):
    label = f'{name} [{tz}]'
    try:
        script = build_script(src, cases)
    except SystemExit as e:
        fail(f'{label}: {e}')
        return
    okay, out, err = run_node(script, tz=tz)
    if not okay:
        fail(f'{label}: node failed -> {err.strip().splitlines()[-1] if err.strip() else "unknown error"}')
        return
    try:
        payload = out.strip().splitlines()[-1]
        results = json.loads(payload)
    except Exception:
        fail(f'{label}: harness produced no parseable result -> {out.strip()[:200]}')
        return
    bad = [r for r in results if not r['pass']]
    for r in bad:
        detail = f" ({r['detail']})" if r['detail'] else ''
        fail(f'{label}: {r["name"]}{detail}')
    NOTE.append(f'{label}: {len(results) - len(bad)}/{len(results)} passed')


def main():
    src = read_index()
    run_suite('recurrence', RECURRENCE_CASES, src)
    run_suite('reminders', REMINDER_CASES, src)
    run_suite('timezone', TZ_CASES, src)
    run_suite('plan-completion', PLAN_DONE_CASES, src)

    # DST is a real risk for calendar maths: run the recurrence suite in four awkward zones,
    # including a Southern-Hemisphere one and Lord Howe (+10:30 / +11 with a 30-minute shift).
    for tz in ('Asia/Beirut', 'America/Santiago', 'Australia/Lord_Howe', 'Europe/London'):
        run_suite('recurrence', RECURRENCE_CASES, src, tz=tz)

    print('ABDO time-logic tests')
    print('-' * 20)
    for n in NOTE:
        print('  · ' + n)
    if FAIL:
        print()
        for f in FAIL:
            print('  FAIL ' + f)
        print(f'\n{len(FAIL)} failure(s)')
        return 1
    print('\n  all time-logic tests pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
