import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "nba-player-props", "scripts"))
import nba_props as m  # noqa: E402

STAR = dict(min=35, pf36=2.4, team='A', team_poss=99.0, s3=0.40, rate_cv=0.05,
            r36=dict(fga=20.0, fta=7.5, reb=5.0, ast=7.0, stl=1.3, blk=0.4, tov=3.2), pct=dict(p2=0.53, p3=0.36, ft=0.86))
BIG = dict(STAR, min=31, pf36=3.8, s3=0.0, r36=dict(fga=11.5, fta=4.5, reb=12.0, ast=3.0, stl=0.8, blk=1.8, tov=2.0),
           pct=dict(p2=0.62, p3=0.30, ft=1.0))
G = dict(exp_margin=4.5, total=231.5, team_poss=99.0)


def test_odds_roundtrip_and_devig():
    assert m.american(m.dec(-110)) == -110 and m.american(m.dec(150)) == 150
    q = m.devig([-115, -105]); assert abs(q.sum()-1) < 1e-9 and q[0] > q[1]
    assert m.breakeven(-110) == pytest.approx(0.5238, abs=1e-4)
    assert m.ev(m.breakeven(-150), -150) == pytest.approx(0.0, abs=1e-12)


def test_whole_number_lines_push():
    x = np.array([24, 25, 25, 26, 27])
    o = m.p_outcomes(x, 25, 'over'); assert o == pytest.approx(dict(win=0.4, push=0.4, loss=0.2))
    u = m.p_outcomes(x, 25, 'under'); assert u == pytest.approx(dict(win=0.2, push=0.4, loss=0.4))
    h = m.p_outcomes(x, 25.5, 'over'); assert h['push'] == 0 and h['win'] == pytest.approx(0.4)
    assert m.breakeven(-110, 0.4) == pytest.approx(0.6/m.dec(-110))


def test_engine_handles_non_shooters_and_perfect_ft():
    S = m.sim_player(BIG, G, n=5000)          # v1 crashed on a 0 three-point share and a 100% FT mark
    assert S['FG3A'].sum() == 0 and np.isfinite(S['PTS']).all()


def test_minutes_mean_matches_input_in_pickem():
    S = m.sim_player(STAR, dict(G, exp_margin=0.0), n=40000)
    assert abs(S['MIN'][np.abs(S['M']) < 10].mean()-STAR['min']) < 0.6


def test_blowouts_cut_star_minutes_and_ot_adds():
    even = m.sim_player(STAR, dict(G, exp_margin=0.0), n=40000)
    lop = m.sim_player(STAR, dict(G, exp_margin=16.0), n=40000)
    assert lop['MIN'].mean() < even['MIN'].mean()-1.0
    assert even['MIN'][even['OT']].mean() > even['MIN'][~even['OT']].mean()+3.5
    assert m.p_ot(0) == pytest.approx(0.070) and m.p_ot(16) < 0.03


def test_minutes_noise_is_left_skewed_for_stars():
    S = m.sim_player(STAR, dict(G, exp_margin=0.0), n=60000)
    d = S['MIN'][~S['OT']]-STAR['min']; q05, q50, q95 = np.quantile(d, [0.05, 0.5, 0.95])
    assert (q50-q05) > (q95-q50)+1.0


def test_points_mean_tracks_rates():
    p = dict(STAR, rate_cv=0.0)
    S = m.sim_player(p, dict(G, exp_margin=0.0, poss=99.0), n=60000)
    fga = S['FGA'].mean(); exp_fga = 20.0*S['MIN'].mean()/36
    assert abs(fga/exp_fga-1) < 0.03


def test_home_court_lifts_assists():
    h = m.sim_player(dict(STAR, home=True), G, n=60000)['AST'].mean()
    a = m.sim_player(dict(STAR, home=False), G, n=60000)['AST'].mean()
    assert 1.02 < h/a < 1.06


def test_final_probs_market_weight():
    S = m.sim_player(STAR, G, n=40000)
    fp = m.final_probs(S['PTS'], 26.5, 'over', quotes=[(26.5, -115, -105)], w_mkt=1.0)
    nv = m.devig([-115, -105])[0]
    assert fp['p_final'] == pytest.approx(nv, abs=0.01)
    fp2 = m.final_probs(S['PTS'], 26.5, 'over', quotes=[(26.5, -115, -105, 'Pinnacle'), (27.5, -110, -110, 'fanduel')])
    assert fp2['p_cons'] != fp2['p_logic']


def test_profit_gate_and_bet_to():
    g = m.profit_gate(0.56, 0.54, -110); assert g['ok'] and g['edge'] == pytest.approx(0.036, abs=1e-3)
    assert not m.profit_gate(0.63, 0.60, -190)['ok']          # 63% at -190 loses money (breakeven 65.5%)
    assert not m.profit_gate(0.56, 0.51, -110)['ok']          # conservative check below breakeven
    price = m.bet_to(0.60); assert m.breakeven(price) == pytest.approx(0.58, abs=0.002)


def test_kelly_caps_the_stake():
    assert m.kelly(0.55, 100) == pytest.approx(0.10)
    assert m.stake_units(6, 0.55, 100, bankroll_units=40) == 1.0
    assert m.stake_units(9, 0.535, -110, bankroll_units=40) == 0.25   # thin edge: small stake whatever the score
    assert m.stake_units(6, 0.50, -110, bankroll_units=40) == 0.0


def test_straight_cap():
    assert m.straight_ok(-190) and m.straight_ok(120) and not m.straight_ok(-195) and not m.straight_ok(None)


def test_pick_top_applies_gate_and_limits():
    c = [dict(id='a', player='A', game='G1', script='s', score=7, p=0.60, p_cons=0.57, price=-120),
         dict(id='b', player='B', game='G1', script='s', score=7, p=0.66, p_cons=0.62, price=-190),   # fails the gate at -190
         dict(id='c', player='C', game='G2', script='t', score=6, p=0.58, p_cons=0.55, price=-105),
         dict(id='d', player='A', game='G3', script='u', score=8, p=0.62, p_cons=0.60, price=-110)]
    ids = [x['id'] for x in m.pick_top(c, 5)]
    assert 'b' not in ids and ids[0] == 'd' and 'a' not in ids           # one bet per player
    assert 'b' in [x['id'] for x in m.pick_top(c, 5, require_edge=False)]


def test_best_offer_prefers_value():
    S = m.sim_player(STAR, G, n=40000)
    rows = m.best_offer(S['PTS'], 'over', [('fanduel', 26.5, -120), ('draftkings', 25.5, -135), ('betmgm', 26.5, -105)])
    assert rows[0]['ev'] >= rows[-1]['ev'] and {r['book'] for r in rows} == {'fanduel', 'draftkings', 'betmgm'}


def test_usage_shift_fitted_rule():
    mates = dict(wing=dict(min=30, r36=dict(fga=13.0, fta=3.0, reb=5.0, ast=2.5)), sub=dict(min=16, promoted=True, r36=dict(fga=10.0, fta=2.0, reb=4.0, ast=2.0)))
    new = m.usage_shift(dict(fga=19.0, ast=7.5, reb=5.0), mates)
    assert new['wing']['r36']['fga'] == pytest.approx(13.0+0.135*(19.0-10.6))
    assert new['wing']['r36']['ast'] == pytest.approx(2.5*1.17)
    assert new['sub']['min'] > 16+8 and new['sub']['min_sd_extra'] > 4
    assert new['wing']['min'] < 31.5


def test_project_minutes_removes_blowouts_and_handles_role_change():
    a = m.project_minutes([36, 36, 36, 36, 26], margins=[3, 2, 5, 4, 30])
    b = m.project_minutes([36, 36, 36, 36, 26])
    assert a['min'] > b['min']
    c = m.project_minutes([18, 17, 19, 18, 18], role_change='promoted')
    assert c['min'] > 26 and c['min_sd_extra'] > 3


def test_project_rate_shrinks_toward_last_season():
    r = m.project_rate('reb', season_total=50, season_min=300, prev_total=600, prev_min=2400)
    assert 36*50/300 < r/m.DRIFT['reb'] < 36*600/2400   # between this season (6.0) and last season (9.0)


def test_same_game_parlay_correlation():
    pg = dict(STAR, r36=dict(STAR['r36'], ast=9.0))
    out = m.sgp([pg, dict(STAR, min=34)], G, [(0, 'AST', 7.5, 'over'), (1, 'PTS', 24.5, 'over')], n=30000)
    assert out['joint'] <= min(1.0, out['independent']*1.3) and out['lift'] > 1.0


def test_parlay_builder_requires_positive_ev():
    rng = np.random.default_rng(0)
    legs = [dict(id=f'L{i}', player=f'P{i}', game=f'G{i}', stat='PTS', side='over', p=0.64, score=7, price=-130,
                 hits=rng.random(1000) < 0.64) for i in range(4)]
    res = m.build_parlays(legs, 'safe')
    assert res and all(r['ev'] >= 0 for r in res)
    bad = [dict(L, price=-400) for L in legs]
    assert m.build_parlays(bad, 'safe') == []


def test_sanity_and_traps():
    S = m.sim_player(STAR, G, n=5000)
    assert m.sanity(S, STAR, G, 'PTS', S['PTS'].mean()+10)
    f = m.trap_flags(dict(side='over', role='star', exp_margin=12, stat='FG3M', exp_3pa=4, usage_line_move=3.0, usage_fair_move=1.2))
    assert len(f) == 3


def test_v1_api_names_still_exist():
    for name in ('sim_player', 'sim_game_players', 'final_probs', 'mkt_mean', 'fit_ladder', 'script_table', 'script_fit', 'sensitivity',
                 'score', 'verdict', 'pick_top', 'build_parlays', 'round_robin', 'house_edge', 'implied_lift', 'clv', 'autoresearch',
                 'replay', 'calibrate_min', 'bet_zones', 'ladder', 'usage_bumps', 'wowy_bump', 'matchup_adj', 'est_price', 'price_note',
                 'best_straight_line', 'screen', 'team_budget', 'hit_rate', 'kalshi_weight', 'market_guard', 'compare_models'):
        assert callable(getattr(m, name))
