from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from aiogram.filters import Command
from bot.database.engine import AsyncSessionLocal
from bot.database.models import BannedUser, Session, MessageMap, AdminState
from bot.config import ADMIN_GROUP_ID

admin_router = Router()

@admin_router.callback_query(F.data.startswith("claim_"))
async def process_claim(callback_query: CallbackQuery, bot: Bot):
    user_id = int(callback_query.data.split("_")[1])
    admin_id = callback_query.from_user.id
    
    async with AsyncSessionLocal() as db:
        session = await db.scalar(select(Session).where(Session.user_id == user_id, Session.is_active == True))
        
        if not session:
            await callback_query.answer("This session is no longer active.", show_alert=True)
            return
            
        if session.admin_id is not None:
            if session.admin_id == admin_id:
                await callback_query.answer("You have already claimed this ticket.", show_alert=True)
            else:
                await callback_query.answer("This ticket was already claimed by someone else.", show_alert=True)
            return
        
        # Assign session
        session.admin_id = admin_id
        
        # Update Admin focus
        admin_state = await db.scalar(select(AdminState).where(AdminState.admin_id == admin_id))
        if not admin_state:
            admin_state = AdminState(admin_id=admin_id, active_user_id=user_id)
            db.add(admin_state)
        else:
            admin_state.active_user_id = user_id
            
        await db.commit()
        
        # Edit the group message
        admin_name = callback_query.from_user.full_name
        try:
            await callback_query.message.edit_text(
                f"{callback_query.message.html_text}\n\n✅ <b>Claimed by {admin_name}</b>",
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception:
            pass # Message might be too old or bot lacks permission
            
        await callback_query.answer("Ticket claimed successfully!")
        
        # Notify the user
        try:
            await bot.send_message(user_id, "An agent has joined the chat. How can we help?")
        except Exception:
            pass
            
        # Notify the admin privately
        try:
            await bot.send_message(admin_id, f"✅ You have claimed the ticket for User ID: {user_id}. You are now focused on this session. Messages sent here will go to the user.")
        except Exception:
            # Note: if admin hasn't started the bot privately, this fails. They need to `/start` it.
            pass

@admin_router.message(Command("close"))
async def cmd_close(message: Message, bot: Bot):
    admin_id = message.from_user.id
    
    async with AsyncSessionLocal() as db:
        admin_state = await db.scalar(select(AdminState).where(AdminState.admin_id == admin_id))
        if not admin_state or not admin_state.active_user_id:
            await message.answer("You do not have any active focused session.")
            return
            
        target_user_id = admin_state.active_user_id
        session = await db.scalar(select(Session).where(Session.user_id == target_user_id, Session.is_active == True))
        
        if session:
            session.is_active = False
        
        admin_state.active_user_id = None
        await db.commit()
        
        await message.answer(f"Session with User ID {target_user_id} has been closed.")
        try:
            await bot.send_message(target_user_id, "Your support session has been closed. Have a great day!")
        except Exception:
            pass

@admin_router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    admin_id = message.from_user.id
    target_user_id = None
    
    async with AsyncSessionLocal() as db:
        # First check if replied to a specific message
        if message.reply_to_message:
            msg_map = await db.scalar(select(MessageMap).where(MessageMap.admin_message_id == message.reply_to_message.message_id))
            if msg_map:
                target_user_id = msg_map.user_id
        
        # Fallback to focused session
        if not target_user_id:
            admin_state = await db.scalar(select(AdminState).where(AdminState.admin_id == admin_id))
            if admin_state and admin_state.active_user_id:
                target_user_id = admin_state.active_user_id

        if not target_user_id:
            await message.answer("Cannot find user to ban. Please reply to a user's message with /ban.")
            return
            
        banned = await db.scalar(select(BannedUser).where(BannedUser.user_id == target_user_id))
        if not banned:
            db.add(BannedUser(user_id=target_user_id))
            
            # Close their active session if any
            session = await db.scalar(select(Session).where(Session.user_id == target_user_id, Session.is_active == True))
            if session:
                session.is_active = False
                
            await db.commit()
            
            await message.answer(f"User ID {target_user_id} has been banned.")
            try:
                await bot.send_message(target_user_id, "You have been banned from using this support bot.")
            except Exception:
                pass
        else:
            await message.answer("User is already banned.")

# We add a generic handler at the bottom for admin's private messages going to the user.
# Crucially, this must be filtered to private chats. The user_router will also trigger if this doesn't.
# Wait! In aiogram, if multiple routers can handle a message, the FIRST one registered wins.
# So admin_router must be registered BEFORE user_router.
@admin_router.message(F.chat.type == "private")
async def process_admin_message(message: Message, bot: Bot):
    # Skip commands explicitly handled here if any got through
    if message.text and message.text.startswith('/'):
        # Usually commands like /start will be handled by user_router because admin_router didn't register /start.
        # But wait! This broad catch-all `process_admin_message` WILL catch `/start` if it's placed here and admin_router is first!
        # Let's ignore /start.
        if message.text.startswith('/start'):
            from .user import cmd_start
            return await cmd_start(message)

    admin_id = message.from_user.id
    target_user_id = None
    target_message_id = None
    
    async with AsyncSessionLocal() as db:
        # Scenario 1: Reply to a specific user message
        if message.reply_to_message:
            msg_map = await db.scalar(select(MessageMap).where(MessageMap.admin_message_id == message.reply_to_message.message_id))
            if msg_map:
                target_user_id = msg_map.user_id
                target_message_id = msg_map.user_message_id
                
                # Update focus
                admin_state = await db.scalar(select(AdminState).where(AdminState.admin_id == admin_id))
                if not admin_state:
                    admin_state = AdminState(admin_id=admin_id, active_user_id=target_user_id)
                    db.add(admin_state)
                else:
                    admin_state.active_user_id = target_user_id
                await db.commit()

        # Scenario 2: Focused user (no reply)
        if not target_user_id:
            admin_state = await db.scalar(select(AdminState).where(AdminState.admin_id == admin_id))
            if admin_state and admin_state.active_user_id:
                target_user_id = admin_state.active_user_id

        # If neither scenario matches, let this pass through so user_router can handle it (this person is acting as a regular user).
        if not target_user_id:
            from .user import process_user_message
            return await process_user_message(message, bot)
            
        # Send to user
        try:
            await bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_to_message_id=target_message_id
            )
        except Exception as e:
            await message.answer(f"Failed to send message: {str(e)}")
