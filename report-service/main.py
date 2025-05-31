from fastapi import FastAPI
app = FastAPI()

dummy_tasks = [
    {"id": 1, "title": "Zadanie A", "is_done": True},
    {"id": 2, "title": "Zadanie B", "is_done": False},
    {"id": 3, "title": "Zadanie C", "is_done": True},
    {"id": 4, "title": "Zadanie D", "is_done": False},
]

@app.get("/report/tasks_summary")
def task_summary():
    total = len(dummy_tasks)
    done = len([t for t in dummy_tasks if t["is_done"]])
    pending = total - done
    return {
        "total_tasks": total,
        "completed_tasks": done,
        "pending_tasks": pending,
        "completion_rate": f"{(done / total * 100):.2f}%"
    }

@app.get("/report/progress_chart_data")
def progress_chart_data():
    return {
        "labels": ["Zakończone", "Do zrobienia"],
        "values": [len([t for t in dummy_tasks if t["is_done"]]),
                   len([t for t in dummy_tasks if not t["is_done"]])]
    }
