"""Best-effort cleanup for messages created by this bot.

Telegram only permits deletion for a limited period; failures are deliberately
ignored because a user may have deleted the message themselves.
"""
def schedule_cleanup(context, message, minutes):
    if not minutes or int(minutes) <= 0:
        return
    context.job_queue.run_once(
        _delete_message, int(minutes) * 60,
        context={"chat_id": message.chat_id, "message_id": message.message_id},
        name=f"cleanup:{message.chat_id}:{message.message_id}")


def _delete_message(context):
    try:
        context.bot.delete_message(**context.job.context)
    except Exception:
        pass
