"""The kill switch (15 Nov, coordinator 15:40 item 16). One switch stops every alert and every member-page / public-feed update at once.
On: the file output/markets/live/EDGES_KILL exists (the Mac; the coordinator can create it through the queue), or the environment
variable EDGES_KILL=1 (GitHub: a repository variable). Every script that sends or publishes calls killed() first and stops if it's on.
Nothing is deleted: turning it off resumes from where things were."""
import os
def killed(T=None):
    T = T or os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20'))
    return os.environ.get('EDGES_KILL') == '1' or os.path.exists(os.path.join(T, 'output/markets/live/EDGES_KILL'))
def stop_if_killed(name, T=None):
    """Call first: prints one line and exits the script if the switch is on."""
    if killed(T):
        print(f'{name}: stopped by the kill switch (EDGES_KILL)', flush=True); raise SystemExit(0)
