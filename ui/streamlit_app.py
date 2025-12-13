import pandas as pd
import streamlit as st

from api_client import create_workout, wait_for_prediction, recent_workouts, daily_stats

st.set_page_config(page_title="FitBurn Rewards", layout="wide")

st.title("FitBurn Counter")
st.caption("How many calories did you burn?")

tab_predict, tab_analytics = st.tabs(["Predict", "Analytics"])


with tab_predict:
    st.subheader("New workout prediction")

    col1, col2, col3 = st.columns(3)

    with col1:
        user_id = st.text_input("User ID", value="katya_1")
        gender = st.selectbox("Gender", ["Female", "Male"])
        age = st.number_input("Age", min_value=0, max_value=120, value=20, step=1)

    with col2:
        height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=168.0, step=1.0)
        weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=250.0, value=55.0, step=1.0)
        ts = st.text_input("Timestamp (ISO, optional)", value="")  # optional; API может принять пустое? если нет — ставим сейчас ниже

    with col3:
        duration_min = st.number_input("Running Time (min)", min_value=1.0, max_value=600.0, value=35.0, step=1.0)
        distance_km = st.number_input("Distance (km)", min_value=0.1, max_value=200.0, value=5.2, step=0.1)
        speed_kmh = st.number_input("Running Speed (km/h)", min_value=0.1, max_value=40.0, value=8.9, step=0.1)
        avg_hr = st.number_input("Average Heart Rate", min_value=0.0, max_value=250.0, value=145.0, step=1.0)

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        run = st.button("Predict calories", type="primary")

    if run:
        payload = {
            "user_id": user_id.strip(),
            "gender": gender,
            "age": int(age),
            "height_cm": float(height_cm),
            "weight_kg": float(weight_kg),
            "ts": ts.strip() if ts.strip() else pd.Timestamp.utcnow().isoformat(),
            "duration_min": float(duration_min),
            "distance_km": float(distance_km),
            "avg_hr": float(avg_hr) if avg_hr > 0 else None,
            "speed_kmh": float(speed_kmh) if speed_kmh > 0 else None,
        }

        try:
            created = create_workout(payload)
            workout_id = created["workout_id"]
            st.info(f"Workout created: {workout_id}. Waiting for prediction...")

            result = wait_for_prediction(workout_id, timeout_sec=25, poll_sec=0.7)

            if result.get("status") == "done":
                cals = result.get("calories_pred")
                st.success(f"Calories burned: **{cals:.1f} kcal**")
                st.write("Model version:", result.get("model_version"))

                points = int(max(0, cals) // 10)
                st.metric("Reward points", points)

            elif result.get("status") == "failed":
                st.error("Prediction failed. Check worker logs.")
            else:
                st.warning(f"Prediction status: {result.get('status')} (try Analytics tab or retry later)")

        except Exception as e:
            st.exception(e)


with tab_analytics:
    st.subheader("History & analytics")

    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 3])
    with col_f1:
        filter_user = st.text_input("Filter by user_id (optional)", value="")
    with col_f2:
        limit = st.slider("Rows", min_value=10, max_value=200, value=50, step=10)
    with col_f3:
        days = st.slider("Days for daily stats", min_value=1, max_value=30, value=7, step=1)
    with col_f4:
        refresh = st.button("Refresh")

    if refresh or True:
        try:
            hist = recent_workouts(limit=limit, user_id=filter_user.strip() or None)
            items = hist.get("items", [])
            df = pd.DataFrame(items)

            if df.empty:
                st.warning("No data yet. Create a prediction in the Predict tab.")
            else:
                for c in ["ts", "pred_created_at", "pred_processed_at"]:
                    if c in df.columns:
                        df[c] = pd.to_datetime(df[c], errors="coerce")

                st.dataframe(
                    df.sort_values("ts", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### Calories distribution")
                done = df[df["status"] == "done"].copy()
                if not done.empty and "calories_pred" in done.columns:
                    st.bar_chart(done["calories_pred"].dropna().astype(float))

                st.markdown("### Daily stats")
                stats = daily_stats(days=days)
                sdf = pd.DataFrame(stats.get("items", []))
                if not sdf.empty:
                    sdf["day"] = pd.to_datetime(sdf["day"])
                    sdf = sdf.sort_values("day")
                    st.line_chart(sdf.set_index("day")[["workouts_cnt", "done_cnt"]])
                    if "avg_calories" in sdf.columns:
                        st.line_chart(sdf.set_index("day")[["avg_calories"]])
                else:
                    st.info("No daily stats yet.")

        except Exception as e:
            st.exception(e)
