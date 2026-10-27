import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy().sort_values(['player_id','date','game_id'])
tp = p.groupby(['team_id','season'])['pace48'].transform('mean'); p['pf_'] = p.pace48/tp
stats = ['pts','reb','ast','fg3m','fg3a','stl','blk','tov']
K = dict(pts=200, reb=100, ast=100, fg3m=200, fg3a=100, stl=600, blk=200, tov=400)
W10 = dict(pts=0.2, reb=0.1, ast=0.3, fg3m=0.1, fg3a=0.4, stl=0.1, blk=0.1, tov=0.1)
ps = p.groupby(['player_id','season'])[stats+['min']].sum()
prev = ps.copy(); prev.index = prev.index.set_levels(prev.index.levels[1]+1, level=1); prev = prev.rename(columns=lambda c: 'prev_'+c)
p = p.join(prev, on=['player_id','season'])
g = p.groupby(['player_id','season'], sort=False)
p['n_min'] = g['min'].cumsum() - p['min']
lg = p.groupby('season').apply(lambda d: d[stats].sum()/d['min'].sum(), include_groups=False)
for s in stats+['min']:
    p[f'l10_{s}'] = g[s].transform(lambda x: x.shift().rolling(10, min_periods=1).sum())
for s in stats:
    cum = g[s].cumsum() - p[s]; obs = cum/p.n_min.replace(0, np.nan)
    prior = np.where(p.prev_min >= 300, p[f'prev_{s}']/p.prev_min, lg.loc[p.season, s].values)
    base = np.where(p.n_min > 0, (np.nan_to_num(obs)*p.n_min + K[s]*prior)/(p.n_min + K[s]), prior)
    l10 = p[f'l10_{s}']/p['l10_min'].replace(0, np.nan)
    p[f'rate_{s}'] = np.where(np.isfinite(l10) & (p.l10_min >= 60), (1-W10[s])*base + W10[s]*np.nan_to_num(l10), base)
# opponent allowed (team-level): what all players facing this defense produced, per possession, season-to-date
tg = p.groupby(['game_id','team_id','opp_id','season','date'])[stats].sum().reset_index()
poss = df.drop_duplicates(['game_id','team_id'])[['game_id','team_id','poss']]
tg = tg.merge(poss, on=['game_id','team_id'])
tg = tg.sort_values('date')
d = tg.groupby(['opp_id','season'])  # defense = opp_id
for s in stats+['poss']:
    tg[f'alw_{s}'] = d[s].cumsum() - tg[s]
tg['alw_n'] = d.cumcount()
lgpp = tg.groupby('season').apply(lambda x: x[stats].sum()/x['poss'].sum(), include_groups=False)
for s in stats:
    tg[f'f_{s}'] = (tg[f'alw_{s}']/tg['alw_poss'])/lgpp.loc[tg.season, s].values
p = p.merge(tg[['game_id','team_id','alw_n']+[f'f_{s}' for s in stats]], on=['game_id','team_id'])
# DvP for starters by position: what opposing starters at the same position produced vs this defense (per 36), season-to-date
st = p[p.starter==1].copy()
st['pos1'] = st['position'].str[0]
dv = st.groupby(['game_id','opp_id','season','date','pos1'])[stats+['min']].sum().reset_index().sort_values('date')
dd = dv.groupby(['opp_id','season','pos1'])
for s in stats+['min']:
    dv[f'dvp_{s}'] = dd[s].cumsum() - dv[s]
lgpos = dv.groupby(['season','pos1']).apply(lambda x: x[stats].sum()/x['min'].sum(), include_groups=False)
for s in stats:
    dv[f'dvpf_{s}'] = (dv[f'dvp_{s}']/dv['dvp_min'])/lgpos.loc[list(zip(dv.season, dv.pos1)), s].values
dv['dvp_n'] = dd.cumcount()
ev = p[(p.season>=2012)&(p['min']>=10)&(p.n_min>=200)&(p.alw_n>=5)].copy()
ev['pos1'] = ev['position'].str[0]
ev = ev.merge(dv[['game_id','opp_id','pos1','dvp_n']+[f'dvpf_{s}' for s in stats]], on=['game_id','opp_id','pos1'], how='left')
print('eval rows', len(ev), 'starter rows with dvp', ev.dvp_n.notna().sum())
for s in stats:
    y = ev[s].values; base = ev[f'rate_{s}'].values*ev['min'].values*ev.pf_.values
    mse0 = np.mean((y-base)**2)
    res = []
    for k in (5, 10, 20, 40, 80):
        for b in (0.5, 0.75, 1.0):
            f = 1 + b*(ev[f'f_{s}'].values - 1)*ev.alw_n.values/(ev.alw_n.values + k)
            res.append((k, b, np.mean((y - base*f)**2)))
    k, b, m = min(res, key=lambda t: t[2])
    # DvP on top of team factor (starters only)
    sm = ev.dvp_n.notna().values & (ev.dvp_n.values >= 5)
    f_team = 1 + b*(ev[f'f_{s}'].values - 1)*ev.alw_n.values/(ev.alw_n.values + k)
    pt = base*f_team
    mse_t = np.mean((y[sm]-pt[sm])**2)
    dres = []
    for kd in (10, 20, 40, 80, 160):
        for bd in (0.25, 0.5, 1.0):
            fd = 1 + bd*(ev[f'dvpf_{s}'].values[sm] - 1)*ev.dvp_n.values[sm]/(ev.dvp_n.values[sm] + kd)
            dres.append((kd, bd, np.mean((y[sm]-pt[sm]*fd)**2)))
    kd, bd, md = min(dres, key=lambda t: t[2])
    print(f'{s:5s} team-opp: best k={k} beta={b} MSE {mse0:.4f} -> {m:.4f} ({(mse0-m)/mse0*100:.2f}% better) | DvP on top (starters): k={kd} beta={bd} MSE {mse_t:.4f} -> {md:.4f} ({(mse_t-md)/mse_t*100:.2f}%)')
# home/away and back-to-back effects on per-minute production (actual / predicted)
for s in ('pts','reb','ast','fg3m'):
    base = ev[f'rate_{s}']*ev['min']*ev.pf_
    r = ev.groupby('home').apply(lambda d: d[s].sum()/ (d[f'rate_{s}']*d['min']*d.pf_).sum(), include_groups=False)
    b2b = ev[ev.rest.notna()].groupby(ev.rest==1).apply(lambda d: d[s].sum()/(d[f'rate_{s}']*d['min']*d.pf_).sum(), include_groups=False)
    print(f'{s}: actual/pred home {r.get(1):.3f} away {r.get(0):.3f} | b2b {b2b.get(True):.3f} rested {b2b.get(False):.3f}')
ev[['player_id','game_id','season','min','pf_']+[f'rate_{s}' for s in stats]+[f'f_{s}' for s in stats]+['alw_n']+stats].to_pickle('data/cache/rates_eval.pkl')
