# Team volume vs the market and the realized script: plays, pass rate, attempts, sacks, scrambles, kneels.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); tv = pd.read_pickle('data/cache/nfl/team_view.pkl'); p = T['plays']
tv = tv[tv.plays.notna() & tv.total_line.notna()].copy().sort_values(['team', 'season', 'week'])
# pregame team tendencies: season-to-date neutral pass rate and plays per game (before this game), shrunk to league
g = tv.groupby(['team', 'season'])
tv['n_prior'] = g.cumcount()
for c in ('plays', 'neutral_db', 'neutral_play', 'pass_att', 'dropbacks'):
    tv[f'cum_{c}'] = g[c].cumsum() - tv[c]
lg_npr = tv.neutral_db.sum()/tv.neutral_play.sum()
tv['npr_pre'] = (tv.cum_neutral_db + 150*lg_npr)/(tv.cum_neutral_play + 150)
tv['plays_pre'] = (tv.cum_plays + 4*tv.plays.mean())/(tv.n_prior + 4)
tv['opp_margin'] = -tv.margin
o = tv[['game_id', 'team', 'plays_pre', 'npr_pre']].rename(columns={'team': 'opp', 'plays_pre': 'opp_plays_pre', 'npr_pre': 'opp_npr_pre'})
tv = tv.merge(o, on=['game_id', 'opp'], how='left')
tv['pass_rate'] = tv.dropbacks/tv.plays
from numpy.linalg import lstsq
d = tv.dropna(subset=['plays_pre', 'opp_plays_pre', 'npr_pre'])
X = np.c_[np.ones(len(d)), d.total_line, d.exp_margin, d.plays_pre, d.opp_plays_pre]
b, *_ = lstsq(X, d.plays, rcond=None); r = d.plays - X@b
print('PLAYS pregame model: const %.2f total %.3f exp_margin %.3f own pace %.3f opp pace %.3f | resid SD %.2f' % (*b, r.std()))
X2 = np.c_[X, d.margin.clip(-28, 28), d.pts]
b2, *_ = lstsq(X2, d.plays, rcond=None); r2 = d.plays - X2@b2
print('PLAYS given realized game: +margin %.3f +own pts %.3f | resid SD %.2f' % (b2[5], b2[6], r2.std()))
# pass rate vs pregame tendency and the realized margin (script)
X3 = np.c_[np.ones(len(d)), d.npr_pre, d.exp_margin, d.margin.clip(-28, 28)]
b3, *_ = lstsq(X3, d.pass_rate, rcond=None); r3 = d.pass_rate - X3@b3
print('PASS RATE: const %.3f + %.3f x neutral PR + %.4f x exp_margin + %.4f x realized margin | resid SD %.3f' % (*b3, r3.std()))
d = d.assign(mb=pd.cut(d.margin, [-60, -17, -10, -4, 3, 10, 17, 60]))
print(d.groupby('mb', observed=True).agg(pass_rate=('pass_rate', 'mean'), plays=('plays', 'mean'), att=('pass_att', 'mean'), rush=('rush_att', 'mean'), n=('plays', 'size')).round(3).to_string())
# sacks per dropback, scrambles per dropback, kneels by realized margin
print('sack rate per dropback %.4f; INT per attempt %.4f' % (d.sacks.sum()/d.dropbacks.sum(), d.ints.sum()/d.pass_att.sum()))
pp = p[~p.two_point_attempt & p.posteam.notna()]
kn = pp.groupby(['game_id', 'posteam']).agg(kneels=('qb_kneel', 'sum'), scr=('qb_scramble', 'sum')).reset_index().rename(columns={'posteam': 'team'})
d = d.merge(kn, on=['game_id', 'team'], how='left')
print('kneels by realized margin:', d.groupby('mb', observed=True)['kneels'].mean().round(2).to_dict())
print('scrambles per dropback %.4f' % (d.scr.sum()/d.dropbacks.sum()))
# attempts dispersion given dropbacks: pass attempts = dropbacks - sacks - scrambles
d['pr_res'] = r3.values
print('pass-rate residual autocorrelation within team-season (is it a stable team trait beyond the prior?):')
d = d.sort_values(['team', 'season', 'week']); d['pr_res_prev'] = d.groupby(['team', 'season'])['pr_res'].shift()
print('  corr(res, previous game res) %.3f' % d[['pr_res', 'pr_res_prev']].dropna().corr().iloc[0, 1])
tv.to_pickle('data/cache/nfl/team_view2.pkl')
