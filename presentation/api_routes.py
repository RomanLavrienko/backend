from fastapi import APIRouter, Request, Form, Response, status, Cookie, Body
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
import jwt
from infrastructure.repositiry.base_repository import AsyncSessionLocal
from infrastructure.repositiry.db_models import OrderORM, UserORM, CategoryORM
from infrastructure.services.user_service import UserService
from infrastructure.services.order_service import OrderService
from infrastructure.services.chat_service import ChatService
from infrastructure.services.message_service import MessageService
from infrastructure.services.auth_service import AuthService
import logging
from sqlalchemy import func

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

router = APIRouter()


class RespondBody(BaseModel):
    message: str
    price: int


class SendMessageBody(BaseModel):
    text: str


@router.post("/api/register")
async def register(
        name: str = Form(...),
        email: str = Form(...),
        nickname: str = Form(...),
        password: str = Form(...),
        password_confirm: str = Form(...),
        specification: str = Form("")
):
    if password != password_confirm:
        return JSONResponse({"error": "Пароли не совпадают"}, status_code=400)
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        auth_service = AuthService(secret_key=SECRET_KEY, user_repo=user_service.user_repo)
        try:
            await auth_service.register(name=name, email=email, nickname=nickname, password=password,
                                        specification=specification)
            token = await auth_service.login(email, password)
            resp = JSONResponse({"success": True})
            resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
            return resp
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/api/login")
async def login(
        response: Response,
        email: str = Form(...),
        password: str = Form(...)
):
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        auth_service = AuthService(secret_key=SECRET_KEY, user_repo=user_service.user_repo)
        try:
            token = await auth_service.login(email, password)
            resp = JSONResponse({"success": True})
            resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
            return resp
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/api/profile/mini")
async def profile_mini(access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"authorized": False})
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        if not nickname:
            return JSONResponse({"authorized": False})
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            user_orm = await user_service.get_user_by_nickname(nickname)
            if not user_orm:
                return JSONResponse({"authorized": False})
            user = user_orm.to_entity() if hasattr(user_orm, 'to_entity') else user_orm
            return JSONResponse({
                "authorized": True,
                "name": user.name,
                "email": user.email,
                "nickname": user.nickname,
                "customer_rating": getattr(user, "customer_rating", 0.0),
                "executor_rating": getattr(user, "executor_rating", 0.0)
            })
    except Exception:
        return JSONResponse({"authorized": False})


@router.post("/api/logout")
async def logout(response: Response):
    response = JSONResponse({"success": True})
    response.delete_cookie("access_token")
    return response


@router.post("/orders/create", response_class=HTMLResponse)
async def create_order_post(
        request: Request,
        title: str = Form(...),
        description: str = Form(...),
        price: int = Form(...),
        term: int = Form(...),
        category: str = Form(...),
        access_token: str = Cookie(None)
):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        if not nickname:
            return RedirectResponse("/login")
        async with AsyncSessionLocal() as session:
            from infrastructure.repositiry.db_models import UserORM
            from sqlalchemy import select
            user_orm = (await session.execute(select(UserORM).where(UserORM.nickname == nickname))).scalar_one_or_none()
            if not user_orm:
                return RedirectResponse("/login")
            # --- КОМИССИЯ публикации заказа ---
            from infrastructure.services.order_service import OrderService
            order_service = OrderService(session)
            commission = await order_service.get_commission_settings(session) or {}
            commission_post_order = int(commission.get('commission_post_order', 200))
            if user_orm.balance < commission_post_order:
                return JSONResponse(
                    {"error": f"Недостаточно средств для публикации заказа. Нужно {commission_post_order} руб."},
                    status_code=400)
            user_orm.balance -= commission_post_order
            await session.commit()
            # ... существующая логика создания заказа ...
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/orders/{order_id}/respond")
async def respond_order(order_id: int, body: RespondBody = Body(...), access_token: str = Cookie(None)):
    message = body.message
    try:
        price = int(getattr(body, 'price', 0) or 0)
    except Exception:
        price = 0
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        order_service = OrderService(session)
        executor = await user_service.get_user_by_nickname(nickname)
        if not executor:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        order = await order_service.get_order(order_id)
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        await order_service.increment_responses(order)
        customer = await user_service.get_user_by_id(order.customer_id)
        if not customer:
            return JSONResponse({"error": "Customer not found"}, status_code=404)
        # --- КОМИССИЯ за отклик ---
        commission = await order_service.get_commission_settings(session) or {}
        commission_response_threshold = int(commission.get('commission_response_threshold', 5000))
        commission_response_percent = float(commission.get('commission_response_percent', 1.0))
        response_fee = 0
        if price > commission_response_threshold:
            response_fee = int(price * commission_response_percent / 100)
            if executor.balance < response_fee:
                return JSONResponse({"error": f"Недостаточно средств для отклика. Нужно {response_fee} руб."},
                                    status_code=400)
            executor.balance -= response_fee
            await session.commit()
        chat = await ChatService(session).get_or_create_chat_between_users(customer.id, executor.id)
        message_service = MessageService(session)
        offer_text = f"{message}\n[Оферта: {price} ₽]"
        await message_service.send_message(chat.id, executor.id, message, type='offer', order_id=order_id,
                                           offer_price=price)
        return JSONResponse({"success": True, "chat_id": chat.id, "response_fee": response_fee})


@router.post("/orders/{order_id}/accept")
async def accept_order(order_id: int, access_token: str = Cookie(None)):
    import logging
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        try:
            user_service = UserService(session)
            order_service = OrderService(session)
            order = await order_service.get_order(order_id)
            if not order:
                return JSONResponse({"error": "Order not found"}, status_code=404)
            customer = await user_service.get_user_by_nickname(nickname)
            if not customer or customer.id != order.customer_id:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
            from infrastructure.repositiry.db_models import MessageORM
            from sqlalchemy import select
            logging.warning(f"ACCEPT_ORDER: order_id={order_id}, customer_id={order.customer_id}, nickname={nickname}")
            msgs = await session.execute(
                select(MessageORM)
                .where(
                    MessageORM.order_id == order_id,
                    MessageORM.type == 'offer',
                    MessageORM.offer_price != None,
                    MessageORM.offer_price > 0,
                    MessageORM.sender_id != order.customer_id
                )
                .order_by(MessageORM.created_at.desc())
            )
            offers = msgs.scalars().all()
            logging.warning(
                f"ACCEPT_ORDER: offers found: {[{'id': o.id, 'order_id': o.order_id, 'type': o.type, 'offer_price': o.offer_price, 'sender_id': o.sender_id} for o in offers]}")
            offer = offers[0] if offers else None
            if not offer:
                return JSONResponse({"error": "Нет подходящего отклика для этого заказа"}, status_code=400)
            executor_id = offer.sender_id
            offer_price = offer.offer_price if hasattr(offer,
                                                       'offer_price') and offer.offer_price is not None else order.price
            # --- КОМИССИИ ---
            commission = await order_service.get_commission_settings(session) or {}
            commission_customer = float(commission.get('commission_customer', 10.0))
            commission_executor = float(commission.get('commission_executor', 5.0))
            total_for_customer = int(offer_price + offer_price * commission_customer / 100)
            if customer.balance < total_for_customer:
                return JSONResponse({"error": "Недостаточно средств на балансе"}, status_code=400)
            customer.balance -= total_for_customer
            order.executor_id = executor_id
            order.status = 'WORK'
            await session.commit()
            executor = await user_service.get_user_by_id(executor_id)
            if executor:
                executor.taken_count += 1
                await session.commit()
            # Удаляем все сообщения-офферы для этого заказа
            await session.execute(
                MessageORM.__table__.delete().where(
                    MessageORM.order_id == order_id,
                    MessageORM.type == 'offer'
                )
            )
            await session.commit()
            return JSONResponse({"success": True, "order_id": order_id, "commission_customer": commission_customer,
                                 "commission_executor": commission_executor, "total_for_customer": total_for_customer,
                                 "offer_price": offer_price})
        except Exception as e:
            logging.exception("ACCEPT_ORDER: Exception occurred")
            return JSONResponse({"error": f"EXCEPTION: {e}"}, status_code=400)


@router.post("/orders/{order_id}/close")
async def close_order(order_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        order_service = OrderService(session)
        user_orm = await user_service.get_user_by_nickname(nickname)
        if not user_orm:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        order = await order_service.get_order(order_id)
        if not order or order.customer_id != user_orm.id:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        if order.status != "OPEN":
            return JSONResponse({"error": "Order already closed"}, status_code=400)
        order.status = "CLOSE"
        await session.commit()
        return JSONResponse({"success": True, "order_id": order_id})


@router.post("/orders/{order_id}/cancel")
async def cancel_order_early(order_id: int, access_token: str = Cookie(None)):
    # Досрочно отменить заказ (заказчик)
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM
        from sqlalchemy import select
        order = (await session.execute(select(OrderORM).where(OrderORM.id == order_id))).scalar_one_or_none()
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        order.status = 'CLOSE'
        await session.commit()
        return JSONResponse({"success": True})


@router.post("/orders/{order_id}/submit_for_review")
async def submit_for_review(order_id: int, access_token: str = Cookie(None)):
    # Исполнитель сдаёт заказ на проверку
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM, UserORM
        from sqlalchemy import select
        order = (await session.execute(select(OrderORM).where(OrderORM.id == order_id))).scalar_one_or_none()
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        user = (await session.execute(select(UserORM).where(UserORM.nickname == nickname))).scalar_one_or_none()
        if not user or user.id != order.executor_id:
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        if order.status != 'WORK':
            return JSONResponse({"error": "Order not in WORK status"}, status_code=400)
        order.status = 'REVIEW'
        await session.commit()
        return JSONResponse({"success": True})


@router.post("/orders/{order_id}/return_to_work")
async def return_to_work(order_id: int, access_token: str = Cookie(None)):
    # Заказчик отправляет заказ на доработку
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM, UserORM
        from sqlalchemy import select
        order = (await session.execute(select(OrderORM).where(OrderORM.id == order_id))).scalar_one_or_none()
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        user = (await session.execute(select(UserORM).where(UserORM.nickname == nickname))).scalar_one_or_none()
        if not user or user.id != order.customer_id:
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        if order.status != 'REVIEW':
            return JSONResponse({"error": "Order not in REVIEW status"}, status_code=400)
        order.status = 'WORK'
        await session.commit()
        return JSONResponse({"success": True})


# Меняю confirm_order: теперь заказчик подтверждает заказ только из REVIEW
@router.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: int, rate: int = Form(5), text: str = Form(''), access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not text or len(text.strip()) < 3:
        return JSONResponse({"error": "Текст отзыва обязателен"}, status_code=400)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM, UserORM, ReviewORM, ChatORM
        from sqlalchemy import select
        order = (await session.execute(select(OrderORM).where(OrderORM.id == order_id))).scalar_one_or_none()
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        if order.status != 'REVIEW':
            return JSONResponse({"error": "Order not in REVIEW status"}, status_code=400)
        customer = (await session.execute(select(UserORM).where(UserORM.id == order.customer_id))).scalar_one_or_none()
        executor = (await session.execute(select(UserORM).where(UserORM.id == order.executor_id))).scalar_one_or_none()
        if not customer or not executor:
            return JSONResponse({"error": "Users not found"}, status_code=404)
        review = ReviewORM(
            type='executor',
            rate=rate,
            text=text,
            sender_id=customer.id,
            recipient_id=executor.id,
            order_id=order.id
        )
        session.add(review)
        # --- КОМИССИЯ исполнителя ---
        from infrastructure.services.order_service import OrderService
        order_service = OrderService(session)
        commission = await order_service.get_commission_settings(session) or {}
        commission_executor = float(commission.get('commission_executor', 5.0))
        offer_price = order.price
        executor_income = int(offer_price - offer_price * commission_executor / 100)
        executor.balance += executor_income
        all_reviews = (await session.execute(select(ReviewORM).where(ReviewORM.recipient_id == executor.id,
                                                                     ReviewORM.type == 'executor'))).scalars().all()
        if all_reviews:
            executor.executor_rating = sum(r.rate for r in all_reviews) / len(all_reviews)
        executor.done_count += 1
        order.status = 'CLOSE'
        order.closed_at = func.now()
        # Добавляем системное сообщение в чат
        chat = (await session.execute(select(ChatORM).where(ChatORM.customer_id == order.customer_id,
                                                            ChatORM.executor_id == order.executor_id))).scalar_one_or_none()
        if chat:
            from infrastructure.services.message_service import MessageService
            message_service = MessageService(session)
            await message_service.send_message(chat.id, customer.id, 'Заказчик оставил отзыв об исполнителе',
                                               type='system')
        await session.commit()
        return JSONResponse(
            {"success": True, "commission_executor": commission_executor, "executor_income": executor_income,
             "offer_price": offer_price})


@router.post("/orders/{order_id}/executor_review")
async def executor_review(order_id: int, rate: int = Form(5), text: str = Form(''), access_token: str = Cookie(None)):
    # Отзыв исполнителя о заказчике
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not text or len(text.strip()) < 3:
        return JSONResponse({"error": "Текст отзыва обязателен"}, status_code=400)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM, UserORM, ReviewORM, ChatORM
        from sqlalchemy import select
        order = (await session.execute(select(OrderORM).where(OrderORM.id == order_id))).scalar_one_or_none()
        if not order:
            return JSONResponse({"error": "Order not found"}, status_code=404)
        if order.status != 'CLOSE':
            return JSONResponse({"error": "Order not closed"}, status_code=400)
        executor = (await session.execute(select(UserORM).where(UserORM.id == order.executor_id))).scalar_one_or_none()
        customer = (await session.execute(select(UserORM).where(UserORM.id == order.customer_id))).scalar_one_or_none()
        if not customer or not executor:
            return JSONResponse({"error": "Users not found"}, status_code=404)
        # Проверяем, оставлял ли уже отзыв
        debug_reviews = (await session.execute(
            select(ReviewORM).where(ReviewORM.order_id == order.id, ReviewORM.type == 'customer'))).scalars().all()
        print(
            f"DEBUG executor_review: order_id={order.id}, executor_id={executor.id}, customer_id={customer.id}, found_reviews={[{'id': r.id, 'sender_id': r.sender_id, 'recipient_id': r.recipient_id} for r in debug_reviews]}")
        existing = (await session.execute(
            select(ReviewORM).where(ReviewORM.order_id == order.id, ReviewORM.type == 'customer',
                                    ReviewORM.sender_id == executor.id))).scalar_one_or_none()
        if existing:
            return JSONResponse({"error": "Already reviewed"}, status_code=400)
        review = ReviewORM(
            type='customer',
            rate=rate,
            text=text,
            sender_id=executor.id,
            recipient_id=customer.id,
            order_id=order.id
        )
        session.add(review)
        # Пересчёт рейтинга заказчика
        all_reviews = (await session.execute(select(ReviewORM).where(ReviewORM.recipient_id == customer.id,
                                                                     ReviewORM.type == 'customer'))).scalars().all()
        if all_reviews:
            customer.customer_rating = sum(r.rate for r in all_reviews) / len(all_reviews)
        # Добавляем системное сообщение в чат
        chat = (await session.execute(select(ChatORM).where(ChatORM.customer_id == order.customer_id,
                                                            ChatORM.executor_id == order.executor_id))).scalar_one_or_none()
        if chat:
            from infrastructure.services.message_service import MessageService
            message_service = MessageService(session)
            await message_service.send_message(chat.id, executor.id, 'Исполнитель оставил отзыв о заказчике',
                                               type='system')
        await session.commit()
        return JSONResponse({"success": True})


@router.post("/chat/{chat_id}/send")
async def send_message(chat_id: int, body: SendMessageBody, access_token: str = Cookie(None)):
    text = body.text
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        message_service = MessageService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        message = await message_service.send_message(chat_id, user.id, text)
        return JSONResponse({"success": True,
                             "message": {"id": message.id, "text": message.text, "sender_id": message.sender_id,
                                         "created_at": str(message.created_at)}})


@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: int, after_id: int = 0, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        message_service = MessageService(session)
        messages = await message_service.get_messages_by_chat(chat_id)
        # Фильтруем только новые сообщения, исключая offer
        new_messages = [
            {"id": m.id, "text": m.text, "sender_id": m.sender_id, "created_at": str(m.created_at)}
            for m in messages if m.id > after_id and getattr(m, 'type', None) != 'offer'
        ]
        return JSONResponse(new_messages)


@router.post("/reviews/{review_id}/edit")
async def edit_review(review_id: int, text: str = Form(...), rate: int = Form(...), access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import ReviewORM, UserORM
        from sqlalchemy import select
        review = (await session.execute(select(ReviewORM).where(ReviewORM.id == review_id))).scalar_one_or_none()
        if not review:
            return JSONResponse({"error": "Review not found"}, status_code=404)
        user = (await session.execute(select(UserORM).where(UserORM.nickname == nickname))).scalar_one_or_none()
        if not user or user.id != review.sender_id:
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        review.text = text
        review.rate = rate
        await session.commit()
        return JSONResponse({"success": True})


@router.post("/reviews/{review_id}/response")
async def respond_review(review_id: int, response: str = Form(...), access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import ReviewORM, UserORM
        from sqlalchemy import select
        review = (await session.execute(select(ReviewORM).where(ReviewORM.id == review_id))).scalar_one_or_none()
        if not review:
            return JSONResponse({"error": "Review not found"}, status_code=404)
        recipient = (
            await session.execute(select(UserORM).where(UserORM.id == review.recipient_id))).scalar_one_or_none()
        user = (await session.execute(select(UserORM).where(UserORM.nickname == nickname))).scalar_one_or_none()
        if not user or not recipient or user.id != recipient.id:
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        review.response = response
        await session.commit()
        return JSONResponse({"success": True})
