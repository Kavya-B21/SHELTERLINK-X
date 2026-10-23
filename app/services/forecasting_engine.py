import os
import math
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

from app.extensions import db
from app.models.shelter import Shelter
from app.models.history import ShelterHistory


class ForecastingEngine:
    """
    AI Engineering engine for disaster shelter demand forecasting,
    capacity pressure estimation, and overcrowding risk classification.
    """

    MIN_SAMPLES_FOR_TRAINING = 20

    @classmethod
    def prepare_dataset(cls) -> pd.DataFrame:
        """
        Extract telemetry observations from database into a pandas DataFrame
        with chronological sorting and lag feature engineering.
        """
        records = ShelterHistory.query.order_by(ShelterHistory.timestamp.asc()).all()
        if not records or len(records) < 5:
            return pd.DataFrame()

        data = []
        for r in records:
            data.append({
                'shelter_id': r.shelter_id,
                'timestamp': r.timestamp,
                'total_capacity': r.total_capacity,
                'current_occupancy': r.current_occupancy,
                'incoming_requests': r.incoming_requests,
                'departures': r.departures,
                'affected_area': r.affected_area,
                'shelter_status': r.shelter_status,
                'is_synthetic': r.is_synthetic
            })

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by=['shelter_id', 'timestamp']).reset_index(drop=True)

        # Feature Engineering: Temporal features
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        # Occupancy ratio
        df['occupancy_ratio'] = (df['current_occupancy'] / df['total_capacity']).clip(0, 1.5)

        # Lag features grouped by shelter
        df['lag_incoming_1h'] = df.groupby('shelter_id')['incoming_requests'].shift(1).fillna(0)
        df['lag_incoming_2h'] = df.groupby('shelter_id')['incoming_requests'].shift(2).fillna(0)
        df['rolling_incoming_3h_mean'] = df.groupby('shelter_id')['incoming_requests'].transform(
            lambda s: s.rolling(window=3, min_periods=1).mean()
        )
        df['rolling_occupancy_delta_3h'] = df.groupby('shelter_id')['current_occupancy'].transform(
            lambda s: s.diff(3).fillna(0)
        )

        # Multi-horizon targets: sum of incoming requests over future horizon (e.g. 1h, 3h, 6h, 12h)
        # Using forward rolling sum
        for h in [1, 3, 6, 12]:
            df[f'target_{h}h'] = df.groupby('shelter_id')['incoming_requests'].transform(
                lambda s: s.iloc[::-1].rolling(window=h, min_periods=1).sum().iloc[::-1]
            ).fillna(0)

        return df

    @classmethod
    def train_and_evaluate(cls, horizon_hours: int = 6) -> dict:
        """
        Train a Random Forest Regressor and a Historical Baseline model using a
        chronological (time-aware) train/test split. Computes MAE, RMSE, and R2.
        """
        df = cls.prepare_dataset()
        target_col = f'target_{horizon_hours}h'

        feature_cols = [
            'total_capacity',
            'current_occupancy',
            'occupancy_ratio',
            'hour_of_day',
            'day_of_week',
            'is_weekend',
            'lag_incoming_1h',
            'lag_incoming_2h',
            'rolling_incoming_3h_mean',
            'rolling_occupancy_delta_3h'
        ]

        if len(df) < cls.MIN_SAMPLES_FOR_TRAINING or target_col not in df.columns:
            return {
                'status': 'insufficient_data',
                'sample_count': len(df),
                'min_required': cls.MIN_SAMPLES_FOR_TRAINING,
                'message': f"Only {len(df)} telemetry observations available. Need at least {cls.MIN_SAMPLES_FOR_TRAINING} for model training.",
                'model_name': 'Historical Average Baseline',
                'metrics': None
            }

        # Clean rows
        clean_df = df.dropna(subset=feature_cols + [target_col])
        if len(clean_df) < cls.MIN_SAMPLES_FOR_TRAINING:
            return {
                'status': 'insufficient_data',
                'sample_count': len(clean_df),
                'min_required': cls.MIN_SAMPLES_FOR_TRAINING,
                'message': "Insufficient complete feature rows after lag generation.",
                'model_name': 'Historical Average Baseline',
                'metrics': None
            }

        # Chronological Split (80% train, 20% test)
        split_idx = int(len(clean_df) * 0.8)
        train_df = clean_df.iloc[:split_idx]
        test_df = clean_df.iloc[split_idx:]

        X_train = train_df[feature_cols]
        y_train = train_df[target_col]
        X_test = test_df[feature_cols]
        y_test = test_df[target_col]

        # 1. Train Random Forest Model
        rf_model = RandomForestRegressor(
            n_estimators=50,
            max_depth=6,
            random_state=42,
            min_samples_split=3
        )
        rf_model.fit(X_train, y_train)

        y_pred_rf = rf_model.predict(X_test)
        y_pred_rf = np.maximum(0, np.round(y_pred_rf, 1))

        # 2. Baseline Model (Historical Mean of target grouped by hour of day or overall mean)
        baseline_mean = y_train.mean()
        y_pred_baseline = np.full_like(y_test, fill_value=baseline_mean)

        # Compute Metrics
        mae_rf = float(mean_absolute_error(y_test, y_pred_rf))
        rmse_rf = float(math.sqrt(mean_squared_error(y_test, y_pred_rf)))
        r2_rf = float(r2_score(y_test, y_pred_rf)) if len(y_test) > 1 and np.var(y_test) > 0 else 0.0

        mae_base = float(mean_absolute_error(y_test, y_pred_baseline))
        rmse_base = float(math.sqrt(mean_squared_error(y_test, y_pred_baseline)))
        r2_base = float(r2_score(y_test, y_pred_baseline)) if len(y_test) > 1 and np.var(y_test) > 0 else 0.0

        # Feature Importances
        importances = [
            {'feature': col.replace('_', ' ').title(), 'importance': round(float(imp) * 100, 2)}
            for col, imp in zip(feature_cols, rf_model.feature_importances_)
        ]
        importances.sort(key=lambda x: x['importance'], reverse=True)

        # Residuals sample for visualization (last 15 test predictions)
        test_samples = []
        for i in range(min(15, len(test_df))):
            idx = -(i + 1)
            test_samples.append({
                'actual': float(y_test.iloc[idx]),
                'predicted_rf': float(y_pred_rf[idx]),
                'predicted_baseline': round(float(y_pred_baseline[idx]), 1),
                'error': round(float(y_pred_rf[idx] - y_test.iloc[idx]), 1)
            })

        return {
            'status': 'success',
            'horizon_hours': horizon_hours,
            'train_samples': len(train_df),
            'test_samples': len(test_df),
            'total_samples': len(clean_df),
            'model_name': 'Random Forest Regressor (Scikit-Learn)',
            'baseline_name': 'Historical Mean Baseline',
            'metrics_rf': {
                'mae': round(mae_rf, 2),
                'rmse': round(rmse_rf, 2),
                'r2': round(max(-1.0, min(1.0, r2_rf)), 3)
            },
            'metrics_baseline': {
                'mae': round(mae_base, 2),
                'rmse': round(rmse_base, 2),
                'r2': round(max(-1.0, min(1.0, r2_base)), 3)
            },
            'improvement_over_baseline_pct': round(
                max(0.0, ((mae_base - mae_rf) / mae_base * 100)) if mae_base > 0 else 0.0, 1
            ),
            'feature_importances': importances,
            'test_samples': list(reversed(test_samples)),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def forecast_shelter_demand(cls, shelter: Shelter, horizon_hours: int = 6) -> dict:
        """
        Generate demand prediction and capacity pressure estimation for a specific shelter.
        Falls back smoothly to historical moving average if model cannot be trained.
        """
        # Fetch recent telemetry for this shelter
        recent_logs = ShelterHistory.query.filter_by(shelter_id=shelter.id)\
            .order_by(ShelterHistory.timestamp.desc()).limit(10).all()

        now = datetime.now(timezone.utc)
        hour = now.hour
        day_of_week = now.weekday()
        is_weekend = 1 if day_of_week in [5, 6] else 0

        total_cap = shelter.total_capacity
        current_occ = shelter.current_occupancy
        occ_ratio = (current_occ / total_cap) if total_cap > 0 else 0.0

        lag1 = recent_logs[0].incoming_requests if len(recent_logs) > 0 else 2
        lag2 = recent_logs[1].incoming_requests if len(recent_logs) > 1 else 2
        
        # Calculate recent departures estimate
        avg_dep_per_hour = (
            sum(r.departures for r in recent_logs) / len(recent_logs)
        ) if recent_logs else 1.0

        # Total recent incoming rate
        recent_incoming_rate = (
            sum(r.incoming_requests for r in recent_logs[:3]) / min(3, len(recent_logs))
        ) if recent_logs else 3.0

        # Determine forecasting strategy
        total_history_count = ShelterHistory.query.count()
        used_model = "Rule-Based Historical Baseline"
        
        if total_history_count >= cls.MIN_SAMPLES_FOR_TRAINING:
            try:
                df = cls.prepare_dataset()
                target_col = f'target_{horizon_hours}h'
                feature_cols = [
                    'total_capacity', 'current_occupancy', 'occupancy_ratio',
                    'hour_of_day', 'day_of_week', 'is_weekend',
                    'lag_incoming_1h', 'lag_incoming_2h',
                    'rolling_incoming_3h_mean', 'rolling_occupancy_delta_3h'
                ]
                clean_df = df.dropna(subset=feature_cols + [target_col])
                
                features_df = pd.DataFrame([[
                    total_cap,
                    current_occ,
                    occ_ratio,
                    hour,
                    day_of_week,
                    is_weekend,
                    lag1,
                    lag2,
                    recent_incoming_rate,
                    (recent_logs[0].current_occupancy - recent_logs[-1].current_occupancy) if len(recent_logs) > 1 else 0
                ]], columns=feature_cols)

                rf = RandomForestRegressor(n_estimators=30, max_depth=5, random_state=42)
                rf.fit(clean_df[feature_cols], clean_df[target_col])
                pred_raw = rf.predict(features_df)[0]
                forecasted_incoming = max(0, int(round(pred_raw)))
                used_model = "Random Forest Regressor (Scikit-Learn)"
            except Exception:
                # Robust fallback to diurnal + capacity factor
                diurnal_factor = 1.3 if (10 <= hour <= 20) else 0.7
                forecasted_incoming = max(1, int(round(recent_incoming_rate * horizon_hours * 0.8 * diurnal_factor)))
                used_model = "Diurnal Historical Baseline (Fallback)"
        else:
            # Baseline calculation
            diurnal_factor = 1.2 if (10 <= hour <= 20) else 0.8
            forecasted_incoming = max(1, int(round(recent_incoming_rate * horizon_hours * 0.7 * diurnal_factor)))
            used_model = "Heuristic Operational Baseline"

        # Estimated departures over horizon
        est_departures = max(0, int(round(avg_dep_per_hour * horizon_hours * 0.5)))

        # Projected occupancy = current + incoming - departures (non-negative)
        projected_occupancy = max(0, current_occ + forecasted_incoming - est_departures)
        projected_utilization = (projected_occupancy / total_cap * 100.0) if total_cap > 0 else 100.0

        # Overcrowding Risk Category
        # Low (<70%), Moderate (70-85%), High (85-95%), Critical (>=95%)
        if projected_utilization >= 95.0 or projected_occupancy >= total_cap:
            risk_category = 'CRITICAL'
            risk_badge = 'danger'
            risk_description = "Extreme overcrowding risk! Projected demand will breach operational capacity."
        elif projected_utilization >= 85.0:
            risk_category = 'HIGH'
            risk_badge = 'warning'
            risk_description = "High capacity pressure. Influx approaching facility threshold."
        elif projected_utilization >= 70.0:
            risk_category = 'MODERATE'
            risk_badge = 'info'
            risk_description = "Moderate utilization expected; manageable capacity buffer."
        else:
            risk_category = 'LOW'
            risk_badge = 'success'
            risk_description = "Low overcrowding risk. Ample headroom available."

        # Key drivers explanation
        key_factors = [
            f"Current utilization is {shelter.utilization_percentage}% ({current_occ}/{total_cap} beds).",
            f"Forecast predicts +{forecasted_incoming} incoming displaced persons in the next {horizon_hours} hours.",
            f"Estimated departures over {horizon_hours}h: {est_departures} persons.",
            f"Projected {horizon_hours}h utilization: {projected_utilization:.1f}% ({projected_occupancy} beds)."
        ]

        return {
            'shelter_id': shelter.id,
            'shelter_code': shelter.shelter_code,
            'shelter_name': shelter.name,
            'horizon_hours': horizon_hours,
            'current_occupancy': current_occ,
            'total_capacity': total_cap,
            'available_capacity': shelter.available_capacity,
            'current_utilization_pct': shelter.utilization_percentage,
            'forecasted_incoming': forecasted_incoming,
            'estimated_departures': est_departures,
            'projected_occupancy': projected_occupancy,
            'projected_utilization_pct': round(projected_utilization, 1),
            'risk_category': risk_category,
            'risk_badge': risk_badge,
            'risk_description': risk_description,
            'used_model': used_model,
            'key_factors': key_factors,
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S UTC')
        }

    @classmethod
    def get_all_shelters_pressure(cls, horizon_hours: int = 6) -> list[dict]:
        """Generate capacity pressure predictions for all active shelters."""
        active_shelters = Shelter.query.filter(Shelter.status != 'Inactive').all()
        results = []
        for s in active_shelters:
            results.append(cls.forecast_shelter_demand(s, horizon_hours=horizon_hours))
        
        # Sort by projected utilization descending
        results.sort(key=lambda x: x['projected_utilization_pct'], reverse=True)
        return results
