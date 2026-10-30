# QB traits: which stabilize (completion %, yards per completion, sack rate, INT rate, scramble rate) and the right shrinkage;
# QB designed runs; defensive tackles dispersion; kicker volume vs the implied team total.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); pg = T['player_games']; p = T['plays']
qb = pg[(pg.position == 'QB') & (pg.pass_att >= 10)].sort_values(['player_id', 'season', 'week']).copy()
qb['dropbacks'] = qb.pass_att + qb.sacked + qb.scrambles
g = qb.groupby(['player_id', 'season'])
def split_half_rel(num, den, min_den):
    # split-half reliability within player-seasons (odd vs even games), Spearman-Brown corrected, plus the implied shrinkage k
    s = qb.assign(h=g.cumcount() % 2).groupby(['player_id', 'season', 'h'])[[num, den]].sum().unstack('h')
    s = s[(s[(den, 0)] >= min_den) & (s[(den, 1)] >= min_den)]
    a, b = s[(num, 0)]/s[(den, 0)], s[(num, 1)]/s[(den, 1)]
    r = np.corrcoef(a, b)[0, 1]; full = 2*r/(1+r); n_half = float(np.median(s[(den, 0)]))
    k = n_half*2*(1-full)/full if full > 0 else np.inf          # reliability = n/(n+k) at the full-season sample
    return round(full, 3), round(k, 0), len(s)
for lab, num, den, mn in (('completion %', 'pass_cmp', 'pass_att', 120), ('yards per attempt', 'pass_yds', 'pass_att', 120),
                          ('TD per attempt', 'pass_td', 'pass_att', 120), ('INT per attempt', 'ints', 'pass_att', 120),
                          ('sacks per dropback', 'sacked', 'dropbacks', 120), ('scrambles per dropback', 'scrambles', 'dropbacks', 120),
                          ('rush attempts per game', 'rush_att', 'pass_att', 120)):
    rel, k, n = split_half_rel(num, den, mn)
    print(f'QB {lab:24s}: season reliability {rel:.3f}, implied prior weight k = {k:.0f} {den} (n={n} QB-seasons)')
# QB rushing yards per game composition: designed runs vs scrambles vs kneels
qr = pg[(pg.position == 'QB') & (pg.pass_att >= 10)]
print('QB per game: rush att %.2f (scrambles %.2f, kneels %.2f), rush yds %.1f' % (qr.rush_att.mean(), qr.scrambles.mean(), qr.kneels.mean(), qr.rush_yds.mean()))
# defenders: combined tackles per game dispersion for every-down LBs/safeties
d = pg[pg.position.isin(['LB', 'ILB', 'MLB', 'OLB', 'S', 'SAF', 'FS', 'SS', 'CB']) & (pg.defense_pct >= 0.8)].copy()
d['pos2'] = np.where(d.position.isin(['LB', 'ILB', 'MLB', 'OLB']), 'LB', np.where(d.position == 'CB', 'CB', 'S'))
key = ['player_id', 'season']; gd = d.groupby(key)
d['m_loo'] = (gd.tackles.transform('sum') - d.tackles)/(gd.tackles.transform('size') - 1)
d = d[gd.tackles.transform('size') >= 8]
for pos_, x in d.groupby('pos2'):
    print(f'{pos_} (80%+ snaps): tackles/game {x.tackles.mean():.2f}, variance/mean around his own average {((x.tackles - x.m_loo)**2).mean()/x.m_loo.mean():.2f}')
# opponent plays drive tackle volume
tv = pd.read_pickle('data/cache/nfl/team_view2.pkl')[['game_id', 'team', 'plays']].rename(columns={'team': 'opp', 'plays': 'opp_plays'})
d = d.merge(tv, left_on=['game_id', 'opp'], right_on=['game_id', 'opp'], how='left')
print('LB tackles per opponent play: %.4f; corr(tackles residual, opponent plays) %.3f' % ((d[d.pos2 == 'LB'].tackles/d[d.pos2 == 'LB'].opp_plays).mean(),
      np.corrcoef(d.tackles - d.m_loo, d.opp_plays.fillna(d.opp_plays.mean()))[0, 1]))
# kickers: FG attempts and kicking points vs the implied team total
k = pg[(pg.fga + pg.xpm) > 0].merge(tv.rename(columns={'opp': 'team', 'opp_plays': 'plays'}), on=['game_id', 'team'], how='left')
k['ib'] = pd.cut(k.implied_pts, [0, 17, 20, 23, 26, 29, 50])
print(k.groupby('ib', observed=True).agg(fga=('fga', 'mean'), fgm=('fgm', 'mean'), xpm=('xpm', 'mean'), kick_pts=('kick_pts', 'mean'), sd=('kick_pts', 'std'), n=('kick_pts', 'size')).round(2).to_string())
