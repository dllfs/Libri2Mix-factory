import numpy as np

from add_factory_noise import actual_snr_db, scale_noise_to_snr


def test_scale_noise_to_target_snrs():
    rng = np.random.default_rng(1234)
    speech = rng.normal(0.0, 0.2, 16000).astype(np.float32)
    noise = rng.normal(0.0, 0.5, 16000).astype(np.float32)

    for target_snr in [0.0, 5.0, 10.0]:
        scaled_noise, scale, measured_snr = scale_noise_to_snr(speech, noise, target_snr)

        assert scale > 0
        assert np.isclose(actual_snr_db(speech, scaled_noise), target_snr, atol=1e-3)
        assert np.isclose(measured_snr, target_snr, atol=1e-3)
