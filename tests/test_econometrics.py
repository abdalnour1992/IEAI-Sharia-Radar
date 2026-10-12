import unittest
import numpy as np
import pandas as pd
from ieai.econometrics import hac_ols, factor_models, panel_model, _within


class EconometricValidation(unittest.TestCase):
    def test_factor_coefficients_recover_known_linear_relation(self):
        rng = np.random.default_rng(3)
        x = np.column_stack([np.ones(300), rng.normal(size=(300,3))])
        truth = np.array([.002, .4, -.2, .1])
        y = x @ truth + rng.normal(scale=.001, size=300)
        result = hac_ols(y,x,["alpha","market_excess","smb","hml"])
        self.assertEqual(result["status"], "computed")
        np.testing.assert_allclose([r["estimate"] for r in result["coefficients"]],truth,atol=.001)

    def test_hac_covariance_matches_independent_statsmodels(self):
        try:
            import statsmodels.api as sm
            from statsmodels.stats.sandwich_covariance import cov_hac
        except ImportError:
            self.skipTest("Independent statsmodels cross-check runs in GitHub CI")
        rng = np.random.default_rng(19)
        x = np.column_stack([np.ones(250),rng.normal(size=(250,3))])
        noise = rng.normal(scale=.1,size=250)
        noise[1:] += .5*noise[:-1]
        y = x @ np.array([.2,.4,.2,.5]) + noise
        result = hac_ols(y,x,["a","b","c","d"],lags=5)
        independent = sm.OLS(y,x).fit()
        np.testing.assert_allclose(result["covariance"],cov_hac(independent,nlags=5,use_correction=False),rtol=1e-10,atol=1e-12)

    def test_unbalanced_within_recovers_dense_fixed_effect_coefficients(self):
        rng = np.random.default_rng(15)
        entities, dates, regressors, outcome = [], [], [], []
        effect_a = rng.normal(size=12); effect_t = rng.normal(size=50)
        for a in range(12):
            for d in range(50):
                if rng.random() < .10: continue
                x = rng.normal(size=2)
                entities.append(a); dates.append(d); regressors.append(x)
                outcome.append(x @ [.3,-.4] + effect_a[a] + effect_t[d] + rng.normal(scale=.01))
        x = np.asarray(regressors); y = np.asarray(outcome)
        within = _within(np.column_stack([y,x]),pd.Series(entities),pd.Series(dates))
        estimate = np.linalg.lstsq(within[:,1:],within[:,0],rcond=None)[0]
        dummies_a = pd.get_dummies(pd.Series(entities),drop_first=True,dtype=float).to_numpy()
        dummies_t = pd.get_dummies(pd.Series(dates),drop_first=True,dtype=float).to_numpy()
        full = np.column_stack([x,np.ones(len(y)),dummies_a,dummies_t])
        independent = np.linalg.lstsq(full,y,rcond=None)[0][:2]
        np.testing.assert_allclose(estimate,independent,atol=1e-9)

    def test_missing_factors_never_produce_fake_alpha(self):
        self.assertEqual(factor_models(pd.DataFrame(),pd.DataFrame())["status"],"missing_factors")

    def test_small_panel_has_no_unsupported_pvalues(self):
        frame = pd.DataFrame(columns=["symbol","date","target_event","score","max_drawdown",
                                      "downside_volatility","amihud","abnormal_turnover"])
        result = panel_model(frame)
        self.assertNotIn("coefficients",result)


if __name__ == "__main__": unittest.main()
