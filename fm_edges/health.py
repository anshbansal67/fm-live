"""Health status for Ansh HQ: one status and when it last changed."""
def overall(checks):
    """checks: {name: (state, why)} -> 'FAIL' if any FAIL, else 'WARN' if any WARN, else 'OK'."""
    st = [v[0] for v in checks.values()]
    return 'FAIL' if 'FAIL' in st else 'WARN' if 'WARN' in st else 'OK'

def since(prev, status, now_iso):
    """Keep the old 'since' while the status is unchanged; reset it when the status changes."""
    return prev.get('since') if prev and prev.get('status') == status and prev.get('since') else now_iso
