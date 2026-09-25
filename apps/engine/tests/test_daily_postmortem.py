from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.daily_postmortem import (
    DailyPredictionDiagnosis,
    PostMortemCategory,
    diagnose_daily_prediction,
    format_intraday_tape_summary,
    run_daily_postmortem,
)


@pytest.fixture
def sample_prediction():
    return {
        "id": "pred-123",
        "target_date": "2026-09-24",
        "ticker": "SPY",
        "model_name": "deepseek-v4-flash",
        "predicted_direction": "DOWN",
        "confidence": 70.0,
        "expected_return_pct": -0.45,
        "rationale": "10-year yield breaking higher will trigger tech selling and push SPY down.",
        "catalysts": ["Yield breakout", "Tech valuation compression"],
        "open_price": 764.0,
        "high_price": 768.0,
        "low_price": 763.5,
        "close_price": 767.5,
        "actual_direction": "UP",
        "is_correct": False,
        "intraday_hit": False,
        "brier_score": 0.49,
        "status": "evaluated",
        "postmortem_evaluated_at": None,
    }


@pytest.fixture
def sample_rth_bars():
    return [
        {"date": "2026-09-24 09:30:00", "open": 764.0, "high": 766.0, "low": 764.0, "close": 765.5},
        {"date": "2026-09-24 10:30:00", "open": 765.5, "high": 767.0, "low": 765.0, "close": 766.5},
        {"date": "2026-09-24 15:30:00", "open": 766.5, "high": 768.0, "low": 766.0, "close": 767.5},
    ]


@pytest.fixture
def sample_close_newsletter():
    return {
        "title": "Bond Rout Refuses to Break: SPY Rallies Regardless",
        "summary": "Equities brushed off higher yields as strong semiconductor earnings lifted markets.",
        "bullet_points": ["Semiconductors led broad rally", "10Y yield topped 5.16%"],
    }


def test_format_intraday_tape_summary(sample_rth_bars):
    tape_str = format_intraday_tape_summary(sample_rth_bars)
    assert "09:30:00" in tape_str
    assert "764.00" in tape_str
    assert "767.50" in tape_str


@pytest.mark.asyncio
async def test_diagnose_daily_prediction_catalyst_inversion(
    sample_prediction, sample_rth_bars, sample_close_newsletter
):
    mock_diagnosis = DailyPredictionDiagnosis(
        category=PostMortemCategory.CATALYST_INVERSION,
        was_predictable=True,
        observed_driver="Semiconductors led broad rally despite yield surge",
        flawed_assumption="Assumed rising yields would automatically cause tech selling",
        actionable_lesson="When semiconductor momentum is strong, do not short SPY solely on yield breakout.",
    )

    mock_luna = MagicMock()
    mock_luna.chat.completions.create = AsyncMock(return_value=mock_diagnosis)

    res = await diagnose_daily_prediction(
        prediction=sample_prediction,
        rth_bars=sample_rth_bars,
        close_newsletter=sample_close_newsletter,
        luna_client=mock_luna,
    )

    assert res.category == PostMortemCategory.CATALYST_INVERSION
    assert res.was_predictable is True
    assert "semiconductor" in res.actionable_lesson.lower()


@pytest.mark.asyncio
async def test_diagnose_daily_prediction_unforeseen_shock(sample_prediction, sample_rth_bars, sample_close_newsletter):
    mock_diagnosis = DailyPredictionDiagnosis(
        category=PostMortemCategory.UNFORESEEN_SHOCK,
        was_predictable=False,
        observed_driver="Mid-day unexpected headline",
        flawed_assumption="Morning setup was standard",
        actionable_lesson="Mid-day news shock could not be anticipated pre-market.",
    )

    mock_luna = MagicMock()
    mock_luna.chat.completions.create = AsyncMock(return_value=mock_diagnosis)

    res = await diagnose_daily_prediction(
        prediction=sample_prediction,
        rth_bars=sample_rth_bars,
        close_newsletter=sample_close_newsletter,
        luna_client=mock_luna,
    )

    assert res.category == PostMortemCategory.UNFORESEEN_SHOCK
    assert res.was_predictable is False


@pytest.mark.asyncio
async def test_run_daily_postmortem_updates_db_and_memories(
    sample_prediction, sample_rth_bars, sample_close_newsletter
):
    mock_supabase = MagicMock()

    # Predictions query mock
    pred_query = MagicMock()
    pred_query.eq.return_value = pred_query
    pred_query.order.return_value = pred_query
    pred_query.limit.return_value = pred_query
    pred_query.execute.return_value = MagicMock(data=[sample_prediction])

    # Newsletter query mock
    news_query = MagicMock()
    news_query.eq.return_value = news_query
    news_query.gte.return_value = news_query
    news_query.lte.return_value = news_query
    news_query.order.return_value = news_query
    news_query.limit.return_value = news_query
    news_query.execute.return_value = MagicMock(data=[sample_close_newsletter])

    # Update query mock
    update_query = MagicMock()
    update_query.update.return_value = update_query
    update_query.eq.return_value = update_query
    update_query.execute.return_value = MagicMock(data=[{"id": "pred-123"}])

    mock_predictions_table = MagicMock()
    mock_predictions_table.select.return_value = pred_query
    mock_predictions_table.update.return_value = update_query

    def table_router(table_name):
        if table_name == "daily_predictions":
            return mock_predictions_table
        elif table_name == "generated_newsletters":
            mock_table = MagicMock()
            mock_table.select.return_value = news_query
            return mock_table
        return MagicMock()

    mock_supabase.table.side_effect = table_router

    mock_diagnosis = DailyPredictionDiagnosis(
        category=PostMortemCategory.CATALYST_INVERSION,
        was_predictable=True,
        observed_driver="Semiconductors led rally",
        flawed_assumption="Assumed yields would compress tech",
        actionable_lesson="Check semiconductor momentum before shorting on yields.",
    )

    mock_luna = MagicMock()
    mock_luna.chat.completions.create = AsyncMock(return_value=mock_diagnosis)

    with (
        patch("analysis.daily_postmortem.get_supabase_client", return_value=mock_supabase),
        patch("analysis.daily_postmortem.get_luna_client", return_value=mock_luna),
        patch(
            "analysis.daily_postmortem.fetch_rth_bars_for_date", new_callable=AsyncMock, return_value=sample_rth_bars
        ),
        patch("analysis.daily_postmortem.add_memory") as mock_add_mem,
    ):
        results = await run_daily_postmortem(
            target_date="2026-09-24",
            force=False,
            client=mock_supabase,
            luna_client=mock_luna,
        )

        assert len(results) == 1
        assert results[0]["postmortem_category"] == "CATALYST_INVERSION"
        assert results[0]["was_predictable"] is True

        # Assert daily_predictions update was called
        mock_predictions_table.update.assert_called_once()
        update_args = mock_predictions_table.update.call_args[0][0]
        assert update_args["postmortem_category"] == "CATALYST_INVERSION"
        assert update_args["postmortem_lesson"] == "Check semiconductor momentum before shorting on yields."
        assert update_args["was_predictable"] is True
        assert "postmortem_evaluated_at" in update_args

        # Assert memory was added because was_predictable=True and category != ACCURATE_CAPTURE
        mock_add_mem.assert_called_once()
        mem_kwargs = mock_add_mem.call_args[1]
        assert mem_kwargs["memory_type"] == "AUTORESEARCH_INSIGHT"
        assert mem_kwargs["metadata"]["scope"] == "daily_predictor"
        assert mem_kwargs["metadata"]["track_id"] == "deepseek-v4-flash"
        assert mem_kwargs["metadata"]["postmortem_category"] == "CATALYST_INVERSION"


@pytest.mark.asyncio
async def test_run_daily_postmortem_skips_already_evaluated_unless_forced(
    sample_prediction, sample_rth_bars, sample_close_newsletter
):
    mock_supabase = MagicMock()

    # Prediction is already evaluated with post-mortem
    already_evaluated = dict(sample_prediction)
    already_evaluated["postmortem_evaluated_at"] = "2026-09-24T22:00:00Z"
    already_evaluated["postmortem_category"] = "ACCURATE_CAPTURE"

    pred_query = MagicMock()
    pred_query.eq.return_value = pred_query
    pred_query.order.return_value = pred_query
    pred_query.limit.return_value = pred_query
    pred_query.execute.return_value = MagicMock(data=[already_evaluated])

    mock_table = MagicMock()
    mock_table.select.return_value = pred_query
    mock_supabase.table.return_value = mock_table

    mock_luna = MagicMock()
    mock_luna.chat.completions.create = AsyncMock()

    with (
        patch("analysis.daily_postmortem.get_supabase_client", return_value=mock_supabase),
        patch("analysis.daily_postmortem.get_luna_client", return_value=mock_luna),
        patch(
            "analysis.daily_postmortem.fetch_rth_bars_for_date", new_callable=AsyncMock, return_value=sample_rth_bars
        ),
        patch("analysis.daily_postmortem.add_memory") as mock_add_mem,
    ):
        results = await run_daily_postmortem(
            target_date="2026-09-24",
            force=False,
            client=mock_supabase,
            luna_client=mock_luna,
        )

        # Skipped because already evaluated
        assert len(results) == 0
        mock_luna.chat.completions.create.assert_not_called()
        mock_add_mem.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_postmortem_missing_newsletter_fallback(sample_prediction, sample_rth_bars):
    mock_supabase = MagicMock()

    pred_query = MagicMock()
    pred_query.eq.return_value = pred_query
    pred_query.order.return_value = pred_query
    pred_query.limit.return_value = pred_query
    pred_query.execute.return_value = MagicMock(data=[sample_prediction])

    # Newsletter query returns empty data
    news_query = MagicMock()
    news_query.eq.return_value = news_query
    news_query.gte.return_value = news_query
    news_query.lte.return_value = news_query
    news_query.order.return_value = news_query
    news_query.limit.return_value = news_query
    news_query.execute.return_value = MagicMock(data=[])

    mock_preds_table = MagicMock()
    mock_preds_table.select.return_value = pred_query
    update_mock = MagicMock()
    update_mock.eq.return_value = update_mock
    update_mock.execute.return_value = MagicMock(data=[])
    mock_preds_table.update.return_value = update_mock

    def table_router(table_name):
        if table_name == "daily_predictions":
            return mock_preds_table
        elif table_name == "generated_newsletters":
            mock_table = MagicMock()
            mock_table.select.return_value = news_query
            return mock_table
        return MagicMock()

    mock_supabase.table.side_effect = table_router

    mock_diagnosis = DailyPredictionDiagnosis(
        category=PostMortemCategory.RANGEBOUND_CHOP,
        was_predictable=False,
        observed_driver="Rangebound tape with no clear macro driver",
        flawed_assumption="Attempted to force direction in 0.15% chop",
        actionable_lesson="On low volatility sessions without catalysts, expect rangebound chop.",
    )

    mock_luna = MagicMock()
    mock_luna.chat.completions.create = AsyncMock(return_value=mock_diagnosis)

    with (
        patch("analysis.daily_postmortem.get_supabase_client", return_value=mock_supabase),
        patch("analysis.daily_postmortem.get_luna_client", return_value=mock_luna),
        patch(
            "analysis.daily_postmortem.fetch_rth_bars_for_date", new_callable=AsyncMock, return_value=sample_rth_bars
        ),
        patch("analysis.daily_postmortem.add_memory") as mock_add_mem,
    ):
        results = await run_daily_postmortem(
            target_date="2026-09-24",
            force=True,
            client=mock_supabase,
            luna_client=mock_luna,
        )

        assert len(results) == 1
        assert results[0]["postmortem_category"] == "RANGEBOUND_CHOP"
        assert results[0]["was_predictable"] is False
        # Not saved to memories because was_predictable=False
        mock_add_mem.assert_not_called()
