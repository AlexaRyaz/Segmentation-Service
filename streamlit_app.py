import streamlit as st
import requests
import pandas as pd

# Конфигурация API
API_BASE_URL = "http://127.0.0.1:8000"
st.set_page_config(layout="wide")


def main():
    st.title("📊 Сервис сегментации пользователей")

    # Инициализация состояния сессии
    if 'selected_segment' not in st.session_state:
        st.session_state.selected_segment = None
    if 'selected_user' not in st.session_state:
        st.session_state.selected_user = None

    # Сайдбар для навигации
    st.sidebar.title("Навигация")
    page = st.sidebar.radio("Go to", ["Пользователи", "Сегменты", "Распределение", "Статистика"])

    if page == "Пользователи":
        show_users_page()
    elif page == "Сегменты":
        show_segments_page()
    elif page == "Распределение":
        show_distribution_page()
    elif page == "Статистика":
        show_statistics_page()


def show_users_page():
    st.header("👥 Управление пользователями")

    # Создание нового пользователя
    with st.expander("➕ Добавить нового пользователя"):
        with st.form("create_user_form"):
            name = st.text_input("Имя", key="user_name")
            email = st.text_input("Email", key="user_email")
            if st.form_submit_button("Создать"):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/users/",
                        json={"name": name, "email": email}
                    )
                    if response.status_code == 201:
                        st.success("Пользователь успешно создан!")
                    else:
                        st.error(response.json().get("detail", "Ошибка"))
                except Exception as e:
                    st.error(f"Не удалось создать пользователя: {str(e)}")

    # Список пользователей
    st.subheader("Список пользователей")
    try:
        users = requests.get(f"{API_BASE_URL}/users/").json()
        users_df = pd.DataFrame(users)

        if not users_df.empty:
            st.session_state.selected_user = st.selectbox(
                "Выберите пользователя",
                users_df['id'],
                format_func=lambda x: f"ID: {x} - {users_df[users_df['id'] == x]['name'].values[0]}"
            )

            selected_user_data = users_df[users_df['id'] == st.session_state.selected_user].iloc[0]
            st.write(f"**Email:** {selected_user_data.get('email', 'N/A')}")

            # Сегменты пользователя
            st.subheader("Сегменты пользователя")
            segments = requests.get(
                f"{API_BASE_URL}/users/{st.session_state.selected_user}/segments"
            ).json()

            if segments:
                segments_df = pd.DataFrame({"Сегменты": segments})
                st.dataframe(segments_df, hide_index=True)
            else:
                st.info("У пользователя нет сегментов")

            # Управление сегментами пользователя
            with st.expander("Управление сегментами пользователя"):
                all_segments = requests.get(f"{API_BASE_URL}/segments/").json()
                segment_names = [s['segment'] for s in all_segments]

                col1, col2 = st.columns(2)
                with col1:
                    add_segment = st.selectbox("Добавить сегмент", segment_names)
                    if st.button("Добавить"):
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/users/{st.session_state.selected_user}/segments/{add_segment}"
                            )
                            if response.status_code == 200:
                                st.success("Сегмент добавлен пользователю!")
                                
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                with col2:
                    if segments:
                        remove_segment = st.selectbox("Удалить сегмент", segments)
                        if st.button("Удалить"):
                            try:
                                response = requests.delete(
                                    f"{API_BASE_URL}/users/{st.session_state.selected_user}/segments/{remove_segment}"
                                )
                                if response.status_code == 200:
                                    st.success("Сегмент удален у пользователя!")

                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        st.info("Нет сегментов для удаления")
        else:
            st.info("В системе не найдено ни одного пользователя")
    except Exception as e:
        st.error(f"Не удалось загрузить пользователей: {str(e)}")


def show_segments_page():
    st.header("🏷️ Управление сегментами")

    # Создание нового сегмента
    with st.expander("➕ Добавить новый сегмент"):
        with st.form("create_segment_form"):
            name = st.text_input("Название", key="segment_name")
            description = st.text_area("Описание", key="segment_desc")
            if st.form_submit_button("Создать сегмент"):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/segments/",
                        json={"segment": name, "description": description}
                    )
                    if response.status_code == 201:
                        st.success("Сегмент создан!")
                    else:
                        st.error(response.json().get("detail", "Ошибка создания сегмента"))
                except Exception as e:
                    st.error(f"Не удалось создать сегмент: {str(e)}")

    # Список сегментов
    st.subheader("Список сегментов")
    try:
        segments = requests.get(f"{API_BASE_URL}/segments/").json()
        segments_df = pd.DataFrame(segments)

        if not segments_df.empty:
            st.session_state.selected_segment = st.selectbox(
                "Выберите сегмент",
                segments_df['segment'],
                format_func=lambda x: f"{x} - {segments_df[segments_df['segment'] == x]['description'].values[0]}"
            )

            selected_segment_data = segments_df[segments_df['segment'] == st.session_state.selected_segment].iloc[0]

            # Информация о сегменте
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"#### {selected_segment_data['segment']}")

            with col2:
                if st.button("Удалить сегмент", type="primary"):
                    try:
                        response = requests.delete(
                            f"{API_BASE_URL}/segments/{st.session_state.selected_segment}"
                        )
                        if response.status_code == 200:
                            st.success("Сегмент удален!")
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")

            # Обновление описания
            with st.expander("✏️ Изменить описание"):
                with st.form("update_desc_form"):
                    new_desc = st.text_area("Новое описание", value=selected_segment_data['description'])
                    if st.form_submit_button("Изменить"):
                        try:
                            response = requests.put(
                                f"{API_BASE_URL}/segments/{st.session_state.selected_segment}/description",
                                params={"new_description": new_desc}
                            )
                            if response.status_code == 200:
                                st.success("Описание изменено!")
                                st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {str(e)}")

            # Пользователи в сегменте
            st.write("#### Пользователи в сегменте")
            try:
                users = requests.get(
                    f"{API_BASE_URL}/segments/{st.session_state.selected_segment}/users"
                ).json()['users']

                if users:
                    users_df = pd.DataFrame({"Username": users})
                    st.dataframe(users_df, hide_index=True)
                else:
                    st.info("Нет пользователей в сегменте")
            except Exception as e:
                st.error(f"Не удалось загрузить пользователей сегмента: {str(e)}")
        else:
            st.info("В системе не найдено ни одного сегмента")
    except Exception as e:
        st.error(f"Не удалось загрузить сегменты: {str(e)}")


def show_distribution_page():
    st.header("Распределение")

    try:
        segments = requests.get(f"{API_BASE_URL}/segments/").json()
        segment_names = [s['segment'] for s in segments]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Распределить сегмент по пользователям")
            segment = st.selectbox("Выберите сегмент", segment_names)
            percent = st.slider("Процент пользователей, на который распределить сегмент", 0, 100, 10)

            if st.button("Распределить по выбранным %"):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/segments/{segment}/distribute",
                        json={"percent": percent}
                    )
                    if response.status_code == 200:
                        st.success(response.json()['message'])
                    else:
                        st.error(response.json().get("detail", "Ошибка распределения"))
                except Exception as e:
                    st.error(f"Не удалось распределить: {str(e)}")

            # Информация о распределении
            st.write("### Информация о распределении")
            try:
                dist_info = requests.get(
                    f"{API_BASE_URL}/segments/{segment}/distribute"
                ).json()
                st.write(f"**Пользователей в сегменте:** {dist_info['user_count']}")
                st.write(f"**Всего пользователей:** {dist_info['total_users']}")
                st.write(f"**Процент распределения:** {dist_info['percent']:.2f}%")
            except Exception as e:
                st.error(f"Ошибка получения информации о распределении: {str(e)}")

        with col2:
            st.subheader("Перенос пользователей между сегментами")
            from_segment = st.selectbox("Из", segment_names, key="from_seg")
            to_segment = st.selectbox("В", segment_names, key="to_seg")

            if st.button("Перенести пользователей"):
                if from_segment == to_segment:
                    st.warning("Выберите разные сегменты")
                else:
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/segments/move_users",
                            json={"from_segment": from_segment, "to_segment": to_segment}
                        )
                        if response.status_code == 200:
                            st.success(response.json()['message'])
                        else:
                            st.error(response.json().get("detail", "Ошибка переноса пользователей"))
                    except Exception as e:
                        st.error(f"Не удалось переместить пользователей: {str(e)}")
    except Exception as e:
        st.error(f"Не удалось загрузить сегменты: {str(e)}")


def show_statistics_page():
    st.header("📈 Статистика")

    try:
        stats = requests.get(f"{API_BASE_URL}/segments/stats").json()

        if stats:
            # Преобразуем статистику в DataFrame
            stats_df = pd.DataFrame(stats)

            # Отображаем таблицу
            st.dataframe(
                stats_df[['segment', 'user_count']].rename(columns={
                    'segment': 'Сегмент',
                    'user_count': 'Количество пользователей'
                }),
                hide_index=True
            )

            # Визуализация
            st.subheader("Визуализация")
            st.bar_chart(stats_df.set_index('segment')['user_count'])
        else:
            st.info("Статистические данные отсутствуют")
    except Exception as e:
        st.error(f"Не удалось загрузить статистику: {str(e)}")


if __name__ == "__main__":
    main()