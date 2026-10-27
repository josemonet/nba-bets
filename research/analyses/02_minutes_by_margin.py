import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy()
p['am'] = p.margin.abs()
# player-season base = mean minutes in competitive regulation games (|margin|<=9), LOO not needed for descriptive deltas (large n)
comp = (p.am <= 9) & (p.ot == 0)
base = p[comp].groupby(['player_id','season','team_id'])['min'].agg(['mean','count']).rename(columns={'mean':'base','count':'n_comp'})
p = p.join(base, on=['player_id','season','team_id'])
p = p[p.n_comp >= 15]
def role(b): return np.select([b>=34, b>=28, b>=18], ['star','starter','rotation'], 'bench')
p['role'] = role(p.base)
p['delta'] = p['min'] - p['base']
reg = p[p.ot==0]
bins = [-0.1,3,6,9,12,15,18,21,24,27,30,35,80]
reg = reg.assign(mb=pd.cut(reg.am, bins))
t = reg.pivot_table(index='mb', columns='role', values='delta', aggfunc='mean', observed=True).round(2)
n = reg.pivot_table(index='mb', columns='role', values='delta', aggfunc='size', observed=True)
print('mean minutes delta vs base by |final margin| (regulation games)\n', t[['star','starter','rotation','bench']].to_string())
print(n[['star','starter','rotation','bench']].to_string())
# separate winners and losers at big margins
reg = reg.assign(side=np.where(reg.margin>0,'win','loss'))
t2 = reg[reg.am>=15].pivot_table(index=['mb','side'], columns='role', values='delta', aggfunc='mean', observed=True).round(2)
print(t2[['star','starter','rotation','bench']].to_string())
# OT minutes added
ot = p[p.ot>0].groupby(['role','ot'])['delta'].agg(['mean','std','size']).round(2)
print('OT deltas\n', ot.to_string())
# residual distribution in competitive regulation games
c = p[(p.am<=9)&(p.ot==0)]
q = c.groupby('role')['delta'].describe(percentiles=[.01,.05,.1,.25,.5,.75,.9,.95,.99]).round(2)
print('competitive-game minutes deltas (in-sample base)\n', q.to_string())
print('share delta < -8:', c.groupby('role')['delta'].apply(lambda s: (s<-8).mean()).round(3).to_dict())
print('share delta < -15:', c.groupby('role')['delta'].apply(lambda s: (s<-15).mean()).round(3).to_dict())
# fouls: minutes deltas by fouls in game for starters
print(c[c.role.isin(['star','starter'])].groupby('pf')['delta'].agg(['mean','size']).round(2).to_string())
p[['player_id','season','team_id','game_id','role','base','delta','am','ot','margin','starter','rest','pf']].to_pickle('data/cache/min_roles.pkl')
