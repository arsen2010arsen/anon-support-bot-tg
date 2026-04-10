from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from bot.database.engine import AsyncSessionLocal
from bot.database.models import BannedUser, Session, MessageMap
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import ADMIN_GROUP_ID

user_router = Router()
user_router.message.filter(F.chat.type == "private")

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Hello! Send a message here and our support team will get back to you anonymously.")

@user_router.message()
async def process_user_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as db:
        # 1. Check if banned
        banned = await db.scalar(select(BannedUser).where(BannedUser.user_id == user_id))
        if banned:
            return

        # 2. To avoid admins triggering user logic when they have an active focus,
        # we let admin_router handle those. `admin_router` should be registered FIRST in main.py,
        # and it will consume the event if the sender is an admin with active_user_id.

        # 3. Check session
        session = await db.scalar(select(Session).where(Session.user_id == user_id, Session.is_active == True))
        
        session_created = False
        if not session:
            # Create new session
            session = Session(user_id=user_id)
            db.add(session)
            await db.commit()
            session_created = True
            
            await message.answer("An agent has been notified and will be joining the chat shortly.")
            
        # 4. Routing
        if session.admin_id is None:
            # Pending state: Forward the request to the admin group
            if ADMIN_GROUP_ID:
                try:
                    if session_created:
                        builder = InlineKeyboardBuilder()
                        builder.button(text="Claim Ticket", callback_data=f"claim_{user_id}")
                        
                        notification = await bot.send_message(
                            chat_id=ADMIN_GROUP_ID,
                            text=f"🚨 <b>New Support Request!</b>\n\nUser ID: <code>{user_id}</code>\n\nPlease claim the ticket to respond.",
                            reply_markup=builder.as_markup(),
                            parse_mode="HTML"
                        )
                    
                    # Forward the actual content so admins see it
                    await bot.copy_message(
                        chat_id=ADMIN_GROUP_ID,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                except Exception as e:
                    # Could happen if bot isn't in group yet
                    pass
            else:
                await message.answer("Support is currently unavailable (ADMIN_GROUP_ID not configured).")
        else:
            # Claimed Session: Forward to the specific admin via private DM
            try:
                sent_msg = await bot.copy_message(
                    chat_id=session.admin_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
                
                # Log mapping for replies
                msg_map = MessageMap(
                    admin_message_id=sent_msg.message_id,
                    user_id=user_id,
                    user_message_id=message.message_id
                )
                db.add(msg_map)
                await db.commit()
            except Exception as e:
                pass
