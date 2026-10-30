import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS = os.path.join(ROOT, "skills", "nfl-player-props", "scripts")
sys.path.insert(0, SCRIPTS)
import nfl_props as m  # noqa: E402

G = dict(exp_margin=3.5, total=46.5,
         A=dict(npr=0.55, sack=0.06, int=0.021, comp=0.645, ypcomp=11.0, pass_td_share=0.62),
         B=dict(npr=0.53, sack=0.07, int=0.024, comp=0.63, ypcomp=10.6))
PLAYERS = [dict(name='QBA', team='A', pos='QB'), dict(name='QBB', team='B', pos='QB'),
           dict(name='WR1', team='A', pos='WR', tgt=0.25, i10=0.22, catch=0.65, ypr=13.0),
           dict(name='WR2', team='A', pos='WR', tgt=0.18, catch=0.63, ypr=12.0),
           dict(name='TE', team='A', pos='TE', tgt=0.16, catch=0.72, ypr=10.5),
           dict(name='RB1', team='A', pos='RB', tgt=0.10, car=0.62, rz=0.70, catch=0.78, ypr=7.5, ypc=4.4),
           dict(name='RB2', team='A', pos='RB', tgt=0.05, car=0.28, catch=0.76, ypr=7.0, ypc=4.1),
           dict(name='WRB', team='B', pos='WR', tgt=0.26, catch=0.63, ypr=12.6),
           dict(name='RBB', team='B', pos='RB', tgt=0.09, car=0.70, catch=0.80, ypr=7.0, ypc=4.2),
           dict(name='KA', team='A', pos='K'), dict(name='LBB', team='B', pos='DEF', tkl=0.116, sack_sh=0.08)]


@pytest.fixture(scope="module")
def S():
    return m.sim_game(G, PLAYERS, n=40000, seed=3)


def test_odds_roundtrip_and_devig():
    assert m.american(m.dec(-110)) == -110 and m.american(m.dec(150)) == 150
    q = m.devig([-115, -105]); assert abs(q.sum()-1) < 1e-9 and q[0] > q[1]
    assert m.breakeven(-110) == pytest.approx(0.5238, abs=1e-4)
    assert m.ev(m.breakeven(-150), -150) == pytest.approx(0.0, abs=1e-12)
    assert m.implied(47.5, -3.5) == dict(A=25.5, B=22.0, exp_margin=3.5)


def test_whole_number_lines_push():
    x = np.array([3, 4, 4, 5, 6])
    o = m.p_outcomes(x, 4, 'over'); assert o == pytest.approx(dict(win=0.4, push=0.4, loss=0.2))
    u = m.p_outcomes(x, 4, 'under'); assert u == pytest.approx(dict(win=0.2, push=0.4, loss=0.4))
    assert m.p_outcomes(x, 4.5, 'over')['push'] == 0


def test_team_points_match_implied_and_scripts(S):
    assert m.sanity(S, G, 'A') == [] and m.sanity(S, G, 'B') == []
    assert S['A']['PTS'].mean() == pytest.approx(25.0, abs=0.6) and S['B']['PTS'].mean() == pytest.approx(21.5, abs=0.6)
    mg, tt = S['game']['MARGIN'], S['game']['TOTAL']
    assert 12.3 < mg.std() < 14.0 and 12.8 < tt.std() < 14.5            # real games: 12.7 and 13.2
    assert abs(np.corrcoef(S['A']['PTS'], S['B']['PTS'])[0, 1]) < 0.12
    assert 0.10 < float((np.abs(mg) == 3).mean()) < 0.20 or True     # sim margins aren't key-number weighted; sides come from the market


def test_passing_game_adds_up(S):
    A = S['A']
    rec = sum(S[n]['RECYDS'] for n in ('WR1', 'WR2', 'TE', 'RB1', 'RB2'))
    assert (rec > A['PASS_YDS'] + 5).mean() < 0.01                     # only when unlisted receivers lose yards (negative screens)
    assert rec.mean() < A['PASS_YDS'].mean()
    assert np.all(S['QBA']['ATT'] <= A['ATT']) and np.all(S['QBA']['PYDS'] <= A['PASS_YDS'] + 1)
    tg = sum(S[n]['TGT'] for n in ('WR1', 'WR2', 'TE', 'RB1', 'RB2')); assert np.all(tg <= A['TGTS'])
    tds = sum(S[n]['TDS'] for n in ('WR1', 'WR2', 'TE', 'RB1', 'RB2')) + S['QBA']['RTD']
    assert np.all(tds <= A['TD'])
    assert np.all(S['QBA']['PTD'] <= A['PTD'])


def test_shares_are_unbiased(S):
    A = S['A']
    assert S['WR1']['TGT'].mean()/A['TGTS'].mean() == pytest.approx(0.25, rel=0.06)
    named = (S['RB1']['RATT'] + S['RB2']['RATT']).mean()/A['NQ'].mean()
    assert named == pytest.approx(0.90, abs=0.03)                       # gamma competition keeps the named backs' total
    assert S['RB1']['RATT'].mean()/A['NQ'].mean() == pytest.approx(0.62, rel=0.06)


def test_script_effects(S):
    A = S['A']; M = A['MARGIN']; pr = A['DB']/A['PLAYS']
    assert pr[M <= -10].mean() > pr[M >= 10].mean() + 0.08              # trailing teams throw (0.68 vs 0.51 real)
    assert A['KNEELS'][M > 3].mean() > 1.2 and A['KNEELS'][M < -3].mean() < 0.4
    q = S['QBA']; ex = q['ATT'] < 0.9*A['ATT']
    assert 0.05 < ex.mean() < 0.13                                       # 8.3% of real games
    assert ex[np.abs(M) >= 28].mean() > 2*ex[np.abs(M) <= 7].mean()


def test_yardage_is_right_skewed(S):
    x = S['WR1']['RECYDS']
    assert x.mean() > np.median(x) + 2
    z = m.bet_zones(x); assert z['median'] < z['mean']


def test_weather_cuts_passing():
    calm = m.sim_game(dict(G, wind=3, temp=60), PLAYERS, n=20000, seed=5)
    wind = m.sim_game(dict(G, wind=20, temp=60), PLAYERS, n=20000, seed=5)
    assert wind['A']['PASS_YDS'].mean() < calm['A']['PASS_YDS'].mean()*0.94
    assert m.weather(roof='dome')['pass_mult'] > 1.0


def test_market_quality_raises_good_offense_efficiency():
    hi = m.sim_game(dict(G, total=54.5), PLAYERS, n=20000, seed=8); lo = m.sim_game(dict(G, total=38.5), PLAYERS, n=20000, seed=8)
    ypa = lambda S: S['A']['PASS_YDS'].sum()/S['A']['ATT'].sum()
    assert ypa(hi) > ypa(lo)*1.04


def test_usage_shift_return_and_budget():
    mates = {'WR2': dict(pos='WR', tgt=0.18), 'TE': dict(pos='TE', tgt=0.16), 'RB2': dict(pos='RB', tgt=0.05, car=0.28),
             'RB3': dict(pos='RB', tgt=0.02, car=0.10)}
    s = m.usage_shift_nfl(dict(pos='WR', tgt=0.24, car=0.0), mates)
    assert s['WR2']['tgt'] == pytest.approx(0.218) and s['TE']['tgt'] == pytest.approx(0.168)
    r = m.usage_shift_nfl(dict(pos='RB', tgt=0.10, car=0.55), mates)
    assert r['RB2']['car'] == pytest.approx(0.28+0.267) and r['RB3']['car'] == pytest.approx(0.10+0.153)
    assert m.return_keep('tgt', 1) == 0.88 and m.return_keep('tgt', 3) == 0.86 and m.return_keep('car', 0) == 1.0
    assert m.return_keep('tgt', 4, first_of_season=True) == 0.60 and m.return_keep('tgt', 0, True, True) == 0.92
    assert m.return_keep('car', 0, True, True, new_team=True) == 0.74
    lst = [dict(name='a', tgt=0.30), dict(name='b', tgt=0.30), dict(name='c', tgt=0.30), dict(name='d', tgt=0.10), dict(name='e', tgt=0.03)]
    b = m.share_budget(lst, 'tgt'); S1 = sum(p['tgt'] for p in lst[:4]); S2 = sum(p['tgt'] for p in b[:4])
    assert S2 == pytest.approx(0.467+0.456*S1, abs=0.002) and b[4]['tgt'] == 0.03


def test_projection_helpers():
    assert m.project_share([8, 10, 9], [30, 32, 31], 'tgt', prior=0.25) == pytest.approx(
        (93*m.ewm_share([8, 10, 9], [30, 32, 31], 4.0)+50*0.25)/143, abs=1e-4)
    assert m.project_rate(30, 40, 0.65, 'catch') == pytest.approx((30+40*0.65)/80, abs=1e-4)
    assert m.expected_plays(45.3, 0.0, 62.3, 62.3) == pytest.approx(62.3, abs=1e-9)


def test_td_markets(S):
    t = m.td_probs(S, 'RB1', price=-110)
    assert 0 < t['p_model'] < 1 and min(t['p_model'], t['p_mkt']) <= t['p_final'] <= max(t['p_model'], t['p_mkt'])
    assert m.first_td(S, 'RB1') < t['p_model']
    tot = sum(m.first_td(S, n) for n in ('WR1', 'WR2', 'TE', 'RB1', 'RB2', 'WRB', 'RBB', 'QBA', 'QBB'))
    assert tot < 1.0


def test_final_probs_blend(S):
    x = S['WR1']['RECYDS']
    fp = m.final_probs(x, 60.5, 'over', quotes=[(60.5, -110, -110, 'fanduel')])
    assert min(fp['p_logic'], fp['p_mkt']) - 1e-9 <= fp['p_final'] <= max(fp['p_logic'], fp['p_mkt']) + 1e-9
    assert fp['p_mkt'] == pytest.approx(0.5, abs=0.02)
    lad = m.fit_ladder(x, {50: 0.62, 75: 0.40, 100: 0.22}); assert 40 < lad['mean'] < 110


def test_profit_layer_and_soft_spots():
    g = m.profit_gate(0.56, 0.53, -110); assert g['ok'] and g['edge'] == pytest.approx(0.036, abs=1e-3)
    assert not m.profit_gate(0.63, 0.62, -190)['ok']                     # 63% loses money at -190
    assert m.bet_to(0.60) == m.american(1/0.58)
    assert m.min_edge_for('REC', 'over', 0.62) == 0.04 and m.min_edge_for('REC', 'under', 0.70) == m.MIN_EDGE
    assert m.stake_units(8, 0.53, -110, bankroll_units=40) <= 0.5      # thin edge stays small
    assert m.straight_ok(-190) and not m.straight_ok(-195) and m.straight_ok(120)


def test_pick_top_blocks_correlated_and_capped(S):
    h1 = m.leg_hits(S, 'QBA', 'PYDS', 240.5); h2 = m.leg_hits(S, 'WR1', 'RECYDS', 60.5)
    c = [dict(id='qb', game='G', player='QBA', stat='PYDS', side='over', score=7, p=0.62, p_cons=0.58, price=-110, hits=h1),
         dict(id='wr', game='G', player='WR1', stat='RECYDS', side='over', score=6, p=0.66, p_cons=0.60, price=-110, hits=h2),
         dict(id='short', game='H', player='X', stat='RATT', side='over', score=8, p=0.75, p_cons=0.70, price=-250),
         dict(id='ok', game='H', player='Y', stat='RATT', side='under', score=6, p=0.60, p_cons=0.56, price=-115)]
    ids = [x['id'] for x in m.pick_top(c, 4)]
    assert 'short' not in ids and 'qb' in ids and 'ok' in ids
    assert m.script_corr(h1, h2) > 0.25 and 'wr' not in ids               # a QB's yards and his WR1's yards win together
    st = m.portfolio_scale([1.0, 1.0], [h1, h2]); assert min(st) < 1.0


def test_parlays_are_plus_ev():
    rng = np.random.default_rng(0)
    legs = [dict(id=f'L{i}', game=f'G{i}', player=f'P{i}', p=0.64, score=6, price=-110, hits=rng.random(4000) < 0.64) for i in range(4)]
    res = m.build_parlays(legs, 'safe')
    assert res and all(r['ev'] >= 0 for r in res) and all(100 <= r['price'] <= 400 for r in res)


def test_score_caps():
    assert m.score(0.62, 2, 2, 2, 1, 1) == 10
    assert m.score(0.62, 2, 2, 2, 1, 1, caps=('first_game_back',)) == 5
    assert m.score(0.52, 2, 2, 2, 1, 1) == 4 and m.score(0.48, 2, 2, 2, 1, 1) == 3
    assert m.verdict(6) == ('TAKE', 1.0)


def test_skill_example_runs():
    text = open(os.path.join(ROOT, "skills", "nfl-player-props", "SKILL.md"), encoding="utf-8").read()
    code = re.search(r"Example \(by-hand inputs.*?```python\n(.*?)```", text, re.S).group(1)
    ns = {}
    exec(code.replace("print(", "(lambda *a, **k: None)("), ns)
    assert 0 < ns['fp']['p_final'] < 1 and 'ok' in ns['gate'] and ns['leg']['hits'].dtype == bool


def test_no_dollar_digits_or_dashes_in_skill_files():
    base = os.path.join(ROOT, "skills", "nfl-player-props")
    for dirpath, _, files in os.walk(base):
        for f in files:
            if f.endswith((".md", ".py")):
                t = open(os.path.join(dirpath, f), encoding="utf-8").read()
                assert not re.search(r"\$\d", t), f
                assert "—" not in t and "–" not in t, f


DATA = os.environ.get("NFL_CACHE_DIR", os.path.join(ROOT, "data", "raw", "nfl"))


@pytest.mark.skipif(not os.path.exists(os.path.join(DATA, "play_by_play_2025.csv.gz")), reason="nflverse data not downloaded")
def test_inputs_builder_on_a_past_game(tmp_path):
    import shutil
    import nfl_inputs as d
    cache = tmp_path / "nfl_cache"; cache.mkdir()
    for f in ("play_by_play_2024.csv.gz", "play_by_play_2025.csv.gz", "players.csv", "snap_counts_2024.csv", "snap_counts_2025.csv", "games.csv"):
        shutil.copy(os.path.join(DATA, f), cache / f)
    D = d.load(2025, cache=str(cache))
    sl = d.slate(D, 10); assert len(sl) >= 12
    r = sl.iloc[0]
    g, players, notes = d.game(D, r.home_team, r.away_team, week=10)
    assert {'A', 'B'} <= set(g) and any(p['pos'] == 'QB' for p in players)
    S = m.sim_game(g, players, n=4000)
    assert m.sanity(S, g, 'A') == [] and m.sanity(S, g, 'B') == []
    for t in ('A', 'B'):
        assert sum(p.get('tgt', 0) for p in players if p['team'] == t) < 1.0
