from fastapi import APIRouter, Request, Form, Response, status, Cookie, HTTPException, Query, Body, Depends, UploadFile, \
    File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from infrastructure.services.auth_service import AuthService
from infrastructure.repositiry.user_repository import UserRepository
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.repositiry.base_repository import AsyncSessionLocal
from infrastructure.repositiry.db_models import OrderORM, UserORM, CategoryORM
from sqlalchemy import select
from pydantic import BaseModel
from infrastructure.services.chat_service import ChatService
from infrastructure.services.user_service import UserService
from infrastructure.services.message_service import MessageService
from typing import Union
import os
import secrets
from infrastructure.repositiry.db_models import ContactRequestORM

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

ADMIN = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_COOKIE = "admin_session"

router = APIRouter()

templates = Jinja2Templates(directory='templates')


class RespondBody(BaseModel):
    message: str


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from infrastructure.repositiry.db_models import OrderORM
        # 1. Срочный заказ
        urgent_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 1500, OrderORM.price <= 10000, OrderORM.term.in_([1, 2]),
                                   OrderORM.status == 'OPEN').order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        urgent_ids = [order.id for order in urgent_orders]
        # 2. Премиум заказ, не совпадающий с срочным
        premium_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 5000, OrderORM.status == 'OPEN',
                                   ~OrderORM.id.in_(urgent_ids)).order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        premium_ids = [order.id for order in premium_orders]
        # 3. Новый заказ, не совпадающий с предыдущими
        exclude_ids = urgent_ids + premium_ids
        new_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 1500, OrderORM.price <= 8000, OrderORM.status == 'OPEN',
                                   ~OrderORM.id.in_(exclude_ids)).order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        # Получаем все категории
        from infrastructure.repositiry.db_models import CategoryORM
        categories_result = await session.execute(select(CategoryORM))
        categories = categories_result.scalars().all()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "new_orders": new_orders,
            "urgent_orders": urgent_orders,
            "premium_orders": premium_orders,
            "categories": categories
        })


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    about_text1 = "TeenFreelance — платформа для молодых специалистов."
    about_text2 = "Мы помогаем школьникам и студентам найти первые заказы и построить портфолио."
    advantages = [
        "Безопасные сделки",
        "Удобный поиск заказов",
        "Поддержка наставников",
        "Современный интерфейс"
    ]
    team = [
        {"name": "Иван Иванов", "description": "Основатель, разработчик"},
        {"name": "Мария Петрова", "description": "Дизайнер"}
    ]
    return templates.TemplateResponse("about.html", {
        "request": request,
        "about_text1": about_text1,
        "about_text2": about_text2,
        "advantages": advantages,
        "team": team,
        "member": team[0]  # для совместимости с шаблоном
    })


@router.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/contacts", response_class=HTMLResponse)
async def contacts(request: Request, access_token: str = Cookie(None), email: str = None):
    contact_requests = []
    user_email = None
    is_admin = False
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            nickname = payload.get("sub")
            if nickname == ADMIN:
                is_admin = True
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(ContactRequestORM).order_by(ContactRequestORM.created_at.desc()))
                    contact_requests = result.scalars().all()
            else:
                # Получаем email пользователя
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
                    user = result.scalar_one_or_none()
                    if user:
                        user_email = user.email
        except Exception:
            pass
    if not is_admin:
        # Если email передан явно (например, через форму поиска), используем его
        if email:
            user_email = email
        # Получаем обращения по email
        if user_email:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContactRequestORM).where(ContactRequestORM.email == user_email).order_by(
                        ContactRequestORM.created_at.desc())
                )
                contact_requests = result.scalars().all()
    contacts = {
        "address": "г. Москва, ул. Примерная, д. 1",
        "phone": "+7 900 000-00-00",
        "email": "info@teenfreelance.ru"
    }
    show_requests = False
    if is_admin:
        show_requests = True
    elif user_email and (email or access_token):
        show_requests = True
    return templates.TemplateResponse("contacts.html",
                                      {"request": request, "contacts": contacts, "contact_requests": contact_requests,
                                       "is_admin": is_admin, "user_email": user_email or "",
                                       "show_requests": show_requests})


@router.post("/contacts/send")
async def send_contact_form(request: Request, name: str = Form(...), email: str = Form(...), message: str = Form(...)):
    async with AsyncSessionLocal() as session:
        contact = ContactRequestORM(name=name, email=email, message=message, status="pending")
        session.add(contact)
        await session.commit()
    # Здесь можно добавить отправку email админу
    return RedirectResponse("/contacts", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/order", response_class=HTMLResponse)
async def order(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})


@router.get("/orders", response_class=HTMLResponse)
async def orders(request: Request, category_id: Union[int, str, None] = Query(None), min_price: int = Query(None),
                 max_price: int = Query(None), sort_by: str = Query("date"), page: int = Query(1),
                 page_size: int = Query(15), access_token: str = Cookie(None)):
    if category_id in (None, ""):
        category_id = None
    else:
        category_id = int(category_id)
    current_nickname = None
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            current_nickname = payload.get("sub")
        except Exception:
            pass
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from infrastructure.repositiry.db_models import OrderORM
        query = select(OrderORM)
        if category_id:
            query = query.where(OrderORM.category_id == category_id)
        if min_price is not None:
            query = query.where(OrderORM.price >= min_price)
        if max_price is not None:
            query = query.where(OrderORM.price <= max_price)
        # Фильтруем только открытые заказы ДО подсчёта total_count и пагинации
        query = query.where(OrderORM.status == 'OPEN')
        if sort_by == "price":
            query = query.order_by(OrderORM.price.desc())
        else:
            query = query.order_by(OrderORM.id.desc())
        # Считаем общее количество заказов (для пагинации)
        count_query = query.with_only_columns(OrderORM.id).order_by(None)
        total_orders = (await session.execute(count_query)).scalars().all()
        total_count = len(total_orders)
        # Пагинация
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await session.execute(query)
        order_orms = result.scalars().all()
        orders = []
        for order in order_orms:
            customer_result = await session.execute(select(UserORM).where(UserORM.id == order.customer_id))
            customer = customer_result.scalar_one_or_none()
            category_result = await session.execute(select(CategoryORM).where(CategoryORM.id == order.category_id))
            category = category_result.scalar_one_or_none()
            orders.append({
                "id": order.id,
                "title": order.name,
                "description": order.description,
                "price": order.price,
                "responses": order.responses,
                "deadline": f"~{order.term} дн." if order.term > 1 else f"~{order.term} день",
                "badge": order.priority.value if hasattr(order.priority, 'value') else str(order.priority),
                "customer": customer.nickname if customer else "",
                "customer_name": customer.name if customer else "",
                "customer_photo": customer.photo if customer and hasattr(customer, 'photo') else None,
                "category": category.name if category else "Без категории",
            })
        categories_result = await session.execute(select(CategoryORM))
        categories = categories_result.scalars().all()
        from infrastructure.repositiry.db_models import OrderORM
        urgent_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 1500, OrderORM.price <= 10000, OrderORM.term.in_([1, 2]),
                                   OrderORM.status == 'OPEN').order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        urgent_ids = [order.id for order in urgent_orders]
        # 2. Премиум заказ, не совпадающий с срочным
        premium_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 5000, OrderORM.status == 'OPEN',
                                   ~OrderORM.id.in_(urgent_ids)).order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        premium_ids = [order.id for order in premium_orders]
        # 3. Новый заказ, не совпадающий с предыдущими
        exclude_ids = urgent_ids + premium_ids
        new_orders = (await session.execute(
            select(OrderORM).where(OrderORM.price >= 1500, OrderORM.price <= 8000, OrderORM.status == 'OPEN',
                                   ~OrderORM.id.in_(exclude_ids)).order_by(OrderORM.id.desc()).limit(1)
        )).scalars().all()
        return templates.TemplateResponse("orders.html", {
            "request": request,
            "orders": orders,
            "categories": categories,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "current_nickname": current_nickname,
            "new_orders": new_orders,  # Добавлено
            "urgent_orders": urgent_orders,  # Добавлено
            "premium_orders": premium_orders,  # Добавлено
        })


@router.get("/orders/create", response_class=HTMLResponse)
async def create_order_page(request: Request, access_token: str = Cookie(None)):
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
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user_orm = result.scalar_one_or_none()
            if not user_orm:
                return RedirectResponse("/login")
            user = user_orm.to_entity()
            return templates.TemplateResponse("create_order.html", {"request": request, "user": user})
    except Exception:
        return RedirectResponse("/login")


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
            from infrastructure.repositiry.db_models import UserORM, OrderORM
            from sqlalchemy import select
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user_orm = result.scalar_one_or_none()
            if not user_orm:
                return RedirectResponse("/login")
            # Получаем или создаём категорию
            from infrastructure.repositiry.db_models import CategoryORM
            cat_result = await session.execute(select(CategoryORM).where(CategoryORM.name == category))
            cat = cat_result.scalar_one_or_none()
            if not cat:
                cat = CategoryORM(name=category)
                session.add(cat)
                await session.commit()
                await session.refresh(cat)
            category_id = cat.id
            new_order = OrderORM(
                name=title,
                description=description,
                price=price,
                customer_id=user_orm.id,
                responses=0,
                term=term,
                priority="BASE",
                status="OPEN",
                category_id=category_id
            )
            session.add(new_order)
            await session.commit()
            return RedirectResponse("/orders", status_code=303)
    except Exception as e:
        print("ORDER CREATE ERROR:", e)
        return RedirectResponse("/orders", status_code=303)


@router.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        from infrastructure.repositiry.db_models import ReviewORM
        from sqlalchemy import select
        user_service = UserService(session)
        users = await user_service.get_all_users()
        # Получаем отзывы всех пользователей одним запросом
        reviews_result = await session.execute(select(ReviewORM))
        all_reviews = reviews_result.scalars().all()
        portfolio_users = []
        for user in users:
            executor_reviews = [r for r in all_reviews if r.recipient_id == user.id and r.type == 'executor']
            if not executor_reviews:
                continue
            executor_rating = round(sum(r.rate for r in executor_reviews) / len(executor_reviews), 2)
            if executor_rating <= 3.0:
                continue
            portfolio_users.append({
                "id": user.id,
                "name": user.name,
                "nickname": user.nickname,
                "photo": user.photo,
                "description": user.description,
                "executor_rating": executor_rating,
                "reviews": executor_reviews
            })
        return templates.TemplateResponse("portfolio.html", {"request": request, "users": portfolio_users})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


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
    try:
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            auth_service = AuthService(secret_key=SECRET_KEY, user_repo=user_repo)
            token = await auth_service.login(email, password)
        resp = JSONResponse({"success": True})
        resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
        return resp
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        if not nickname:
            return RedirectResponse("/login")
        async with AsyncSessionLocal() as session:
            from infrastructure.repositiry.db_models import UserORM, OrderORM
            from sqlalchemy import select
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user_orm = result.scalar_one_or_none()
            if not user_orm:
                return RedirectResponse("/login")
            user = user_orm.to_entity()
            # Получаем все заказы пользователя (открытые и закрытые)
            orders_result = await session.execute(select(OrderORM).where(OrderORM.customer_id == user_orm.id))
            user_orders = orders_result.scalars().all()
            orders = []
            for order in user_orders:
                status_val = order.status.value if hasattr(order.status, 'value') else str(order.status)
                if status_val == "OPEN":
                    orders.append({
                        "id": order.id,
                        "title": order.name,
                        "description": order.description,
                        "price": order.price,
                        "status": status_val,
                        "can_close": True,
                    })
            # Получаем активные заказы, где пользователь исполнитель и статус WORK
            active_exec_result = await session.execute(
                select(OrderORM).where(OrderORM.executor_id == user_orm.id, OrderORM.status == 'WORK'))
            active_exec_orders = active_exec_result.scalars().all()
            active_exec = []
            from infrastructure.services.chat_service import ChatService
            chat_service = ChatService(session)
            for order in active_exec_orders:
                # Находим чат между заказчиком и исполнителем
                chat = await chat_service.get_chat_between_users(order.customer_id, order.executor_id)
                chat_id = chat.id if chat else None
                active_exec.append({
                    "id": order.id,
                    "title": order.name,
                    "description": order.description,
                    "price": order.price,
                    "status": "WORK",
                    "chat_id": chat_id
                })
            # Получаем отзывы, где пользователь — получатель
            from infrastructure.repositiry.db_models import ReviewORM
            reviews_result = await session.execute(select(ReviewORM).where(ReviewORM.recipient_id == user_orm.id))
            reviews = reviews_result.scalars().all()
            reviews_data = []
            for r in reviews:
                reviews_data.append({
                    "id": r.id,
                    "rate": r.rate,
                    "text": r.text,
                    "type": r.type,
                    "sender_id": r.sender_id,
                    "order_id": r.order_id,
                    "created_at": r.created_at,
                    "response": r.response
                })
            return templates.TemplateResponse("profile.html", {"request": request, "user": user, "orders": orders,
                                                               "active_exec": active_exec, "reviews": reviews_data,
                                                               "current_user_id": user_orm.id})
    except Exception:
        return RedirectResponse("/login")


@router.post("/orders/{order_id}/close")
async def close_order(order_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        if not nickname:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        async with AsyncSessionLocal() as session:
            from infrastructure.repositiry.db_models import UserORM, OrderORM
            from sqlalchemy import select
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user_orm = result.scalar_one_or_none()
            if not user_orm:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            order_result = await session.execute(
                select(OrderORM).where(OrderORM.id == order_id, OrderORM.customer_id == user_orm.id))
            order = order_result.scalar_one_or_none()
            if not order:
                return JSONResponse({"error": "Order not found"}, status_code=404)
            if order.status != "OPEN":
                return JSONResponse({"error": "Order already closed"}, status_code=400)
            order.status = "CLOSE"
            await session.commit()
            # Возвращаем id закрытого заказа, чтобы удалить его на фронте
            return JSONResponse({"success": True, "order_id": order_id})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
            from infrastructure.repositiry.db_models import UserORM
            from sqlalchemy import select
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user_orm = result.scalar_one_or_none()
            if not user_orm:
                return JSONResponse({"authorized": False})
            user = user_orm.to_entity() if hasattr(user_orm, 'to_entity') else user_orm
            return JSONResponse({
                "authorized": True,
                "name": user.name,
                "nickname": user.nickname,
                "email": user.email,
                "customer_rating": getattr(user, "customer_rating", 0.0),
                "executor_rating": getattr(user, "executor_rating", 0.0),
                "balance": getattr(user, "balance", 0.0)
            })
    except Exception:
        return JSONResponse({"authorized": False})


@router.post("/api/logout")
async def logout(response: Response):
    response = JSONResponse({"success": True})
    response.delete_cookie("access_token")
    return response


@router.get("/chats", response_class=HTMLResponse)
async def chats(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        if not nickname:
            return RedirectResponse("/login")
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            chat_service = ChatService(session)
            message_service = MessageService(session)
            user_orm = await user_service.get_user_by_nickname(nickname)
            if not user_orm:
                return RedirectResponse("/login")
            user = user_orm.to_entity() if hasattr(user_orm, 'to_entity') else user_orm
            chat_orms = await chat_service.get_user_chats(user.id)
            chats = []
            for chat in chat_orms:
                if chat.customer_id == user.id:
                    other_id = chat.executor_id
                else:
                    other_id = chat.customer_id
                other = await user_service.get_user_by_id(other_id)
                other_name = other.nickname if other else "Пользователь"
                messages = await message_service.get_messages_by_chat(chat.id)
                last_message = messages[-1].text if messages else "..."
                date = chat.created_at.strftime('%d.%m.%Y')
                chats.append({
                    "id": chat.id,
                    "name": other_name,
                    "last_message": last_message,
                    "avatar": "",
                    "date": date
                })
            return templates.TemplateResponse("chats.html", {"request": request, "user": user, "chats": chats})
    except Exception:
        return RedirectResponse("/login")


@router.get("/chat/{chat_id}", response_class=HTMLResponse)
async def chat_page(chat_id: int, request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        chat_service = ChatService(session)
        user_service = UserService(session)
        message_service = MessageService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return RedirectResponse("/login")
        chat_orms = await chat_service.get_user_chats(user.id)
        chats = []
        for c in chat_orms:
            if c.customer_id == user.id:
                other_id = c.executor_id
            else:
                other_id = c.customer_id
            other = await user_service.get_user_by_id(other_id)
            other_name = other.nickname if other else "Пользователь"
            messages = await message_service.get_messages_by_chat(c.id)
            last_message = messages[-1].text if messages else "..."
            date = c.created_at.strftime('%d.%m.%Y')
            chats.append({
                "id": c.id,
                "name": other_name,
                "last_message": last_message,
                "avatar": "",
                "date": date
            })
        # Выбираем нужный чат по chat_id
        chat = next((c for c in chat_orms if c.id == chat_id), None)
        if not chat:
            return RedirectResponse("/chats")
        messages = await message_service.get_messages_by_chat(chat.id)
        # Получаем отзывы по заказу для проверки наличия отзыва заказчика
        from infrastructure.repositiry.db_models import ReviewORM
        reviews_result = await session.execute(
            select(ReviewORM).where(ReviewORM.order_id.in_([o.id for o in chats if hasattr(o, 'id')])))
        reviews = reviews_result.scalars().all() if reviews_result else []
        # Оффер ищем только для отображения текста
        last_offer = None
        for msg in reversed(messages):
            if getattr(msg, 'type', None) == 'offer' and getattr(msg, 'order_id', None):
                last_offer = msg
                break
        # Новый способ: ищем заказ по order_id из оффера, если он есть, иначе ищем по паре пользователей с приоритетом статусов
        order = None
        if last_offer and getattr(last_offer, 'order_id', None):
            order_result = await session.execute(
                select(OrderORM).where(OrderORM.id == last_offer.order_id)
            )
            order = order_result.scalar_one_or_none()
        else:
            order_result = await session.execute(
                select(OrderORM).where(
                    ((OrderORM.customer_id == chat.customer_id) & (OrderORM.executor_id == chat.executor_id)) |
                    ((OrderORM.customer_id == chat.executor_id) & (OrderORM.executor_id == chat.customer_id)),
                    OrderORM.status.in_(['REVIEW', 'WORK', 'OPEN', 'CLOSE'])
                )
            )
            # Приоритет: REVIEW > WORK > OPEN > CLOSE
            orders = list(order_result.scalars())
            status_priority = {'REVIEW': 1, 'WORK': 2, 'OPEN': 3, 'CLOSE': 4}
            orders.sort(key=lambda o: status_priority.get(o.status, 99))
            for o in orders:
                if o.status == 'CLOSE':
                    has_customer_review = False
                    for r in reviews:
                        if r.order_id == o.id and r.type == 'executor' and r.sender_id == chat.customer_id:
                            has_customer_review = True
                            break
                    if not has_customer_review:
                        order = o
                        break
                else:
                    order = o
                    break
        # После определения order — всегда добавляем отзывы по этому order (даже если его нет в chats)
        if order:
            order_reviews_result = await session.execute(select(ReviewORM).where(ReviewORM.order_id == order.id))
            order_reviews = order_reviews_result.scalars().all()
            reviews_ids = set((r.id for r in reviews))
            for r in order_reviews:
                if r.id not in reviews_ids:
                    reviews.append(r)
        # Теперь проверяем, нужно ли скрыть order
        if order and order.status == 'CLOSE':
            has_executor_review = any(r.order_id == order.id and r.type == 'executor' for r in reviews)
            has_customer_review = any(r.order_id == order.id and r.type == 'customer' for r in reviews)
            if has_executor_review and has_customer_review:
                order = None
        # Определяем customer и executor для шаблона (перемещаю сюда, чтобы всегда были определены)
        if chat.customer_id == user.id:
            customer = user
            executor = await user_service.get_user_by_id(chat.executor_id)
        else:
            executor = user
            customer = await user_service.get_user_by_id(chat.customer_id)
        return templates.TemplateResponse("chat.html",
                                          {"request": request, "chat": chat, "customer": customer, "executor": executor,
                                           "chats": chats, "chat_id": chat_id, "messages": messages, "user": user,
                                           "order": order, "last_offer": last_offer, "reviews": reviews})


@router.get("/orders/{order_id}/edit", response_class=HTMLResponse)
async def edit_order_page(order_id: int, request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # Проверяем, что заказ принадлежит текущему пользователю
        customer_result = await session.execute(select(UserORM).where(UserORM.id == order.customer_id))
        customer = customer_result.scalar_one_or_none()
        if not customer or customer.nickname != nickname:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return templates.TemplateResponse("edit_order.html", {"request": request, "order": order})


@router.post("/orders/{order_id}/edit")
async def edit_order_post(order_id: int, request: Request, title: str = Form(...), description: str = Form(...),
                          access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        customer_result = await session.execute(select(UserORM).where(UserORM.id == order.customer_id))
        customer = customer_result.scalar_one_or_none()
        if not customer or customer.nickname != nickname:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        if len(description) > 250:
            return JSONResponse({"error": "Описание не должно превышать 250 символов"}, status_code=400)
        order.name = title
        order.description = description
        await session.commit()
        return RedirectResponse("/profile", status_code=303)


@router.post("/orders/{order_id}/favorite")
async def add_favorite_order(order_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        from infrastructure.services.order_service import OrderService
        user_service = UserService(session)
        order_service = OrderService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        await order_service.add_favorite(user.id, order_id)
        return JSONResponse({"success": True})


@router.post("/orders/{order_id}/unfavorite")
async def remove_favorite_order(order_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        from infrastructure.services.order_service import OrderService
        user_service = UserService(session)
        order_service = OrderService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        await order_service.remove_favorite(user.id, order_id)
        return JSONResponse({"success": True})


@router.get("/favorites", response_class=HTMLResponse)
async def favorites(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        from infrastructure.services.order_service import OrderService
        user_service = UserService(session)
        order_service = OrderService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return RedirectResponse("/login")
        favs = await order_service.get_favorites(user.id)
        # Получаем сами заказы
        order_ids = [f.order_id for f in favs]
        if not order_ids:
            orders = []
        else:
            result = await session.execute(
                select(OrderORM).where(OrderORM.id.in_(order_ids), OrderORM.status == 'OPEN'))
            orders = result.scalars().all()
        return templates.TemplateResponse("favorites.html", {"request": request, "orders": orders})


@router.get("/user/{nickname}", response_class=HTMLResponse)
async def public_profile(nickname: str, request: Request, access_token: str = Cookie(None)):
    current_user_id = None
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            current_nickname = payload.get("sub")
            if current_nickname:
                from infrastructure.services.user_service import UserService
                async with AsyncSessionLocal() as session2:
                    user_service = UserService(session2)
                    current_user = await user_service.get_user_by_nickname(current_nickname)
                    if current_user:
                        current_user_id = current_user.id
        except Exception:
            pass
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import UserORM, OrderORM, ReviewORM
        from sqlalchemy import select
        user_result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
        user = user_result.scalar_one_or_none()
        if not user:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        orders_result = await session.execute(select(OrderORM).where(OrderORM.customer_id == user.id))
        user_orders = orders_result.scalars().all()
        reviews_result = await session.execute(select(ReviewORM).where(ReviewORM.recipient_id == user.id))
        reviews = list(reviews_result.scalars().all())
        executor_reviews = [r for r in reviews if r.type == 'executor']
        customer_reviews = [r for r in reviews if r.type == 'customer']
        executor_rating = round(sum(r.rate for r in executor_reviews) / len(executor_reviews),
                                2) if executor_reviews else 0
        customer_rating = round(sum(r.rate for r in customer_reviews) / len(customer_reviews),
                                2) if customer_reviews else 0
        return templates.TemplateResponse("user_profile.html",
                                          {"request": request, "user": user, "orders": user_orders, "reviews": reviews,
                                           "current_user_id": current_user_id, "executor_rating": executor_rating,
                                           "customer_rating": customer_rating})


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_page(order_id: int, request: Request, access_token: str = Cookie(None)):
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM, UserORM, CategoryORM
        from infrastructure.services.order_service import OrderService
        from sqlalchemy import select
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        customer_result = await session.execute(select(UserORM).where(UserORM.id == order.customer_id))
        customer = customer_result.scalar_one_or_none()
        category_result = await session.execute(select(CategoryORM).where(CategoryORM.id == order.category_id))
        category = category_result.scalar_one_or_none()
        # Проверяем избранность и владельца
        is_favorite = False
        is_owner = False
        if access_token:
            try:
                payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
                nickname = payload.get("sub")
                from infrastructure.services.user_service import UserService
                user_service = UserService(session)
                user = await user_service.get_user_by_nickname(nickname)
                if user:
                    is_owner = (user.id == order.customer_id)
                    order_service = OrderService(session)
                    is_favorite = await order_service.is_favorite(user.id, order_id)
            except Exception:
                pass
        if is_owner:
            return RedirectResponse("/profile")
        return templates.TemplateResponse("order.html", {
            "request": request,
            "order": order,
            "customer": customer,
            "category": category,
            "order_term": order.term if hasattr(order, 'term') else None,
            "is_favorite": is_favorite
        })


@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_page(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        user_service = UserService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return RedirectResponse("/login")
        return templates.TemplateResponse("edit_profile.html", {"request": request, "user": user})


@router.post("/profile/edit", response_class=HTMLResponse)
async def edit_profile_post(request: Request,
                            name: str = Form(...),
                            description: str = Form(...),
                            photo: UploadFile = File(None),
                            access_token: str = Cookie(None)):
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return RedirectResponse("/login")
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        user_service = UserService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return RedirectResponse("/login")
        user.name = name
        user.description = description
        # Сохраняем фото, если загружено
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1]
            filename = f"user_{user.id}{ext}"
            path = os.path.join("assets", "images", filename)
            with open(path, "wb") as f:
                f.write(await photo.read())
            user.photo = filename
        await session.commit()
        return RedirectResponse("/profile", status_code=303)


@router.post("/chat/start/{user_id}")
async def start_chat(user_id: int, access_token: str = Cookie(None)):
    if not access_token:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
    except Exception:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    async with AsyncSessionLocal() as session:
        from infrastructure.services.user_service import UserService
        from infrastructure.services.chat_service import ChatService
        user_service = UserService(session)
        chat_service = ChatService(session)
        user = await user_service.get_user_by_nickname(nickname)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        # user_id — это собеседник (customer/executor)
        chat = await chat_service.get_or_create_chat_between_users(user.id, user_id)
        return JSONResponse({"chat_id": chat.id})


@router.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.post("/admin", response_class=HTMLResponse)
async def admin_login(request: Request, login: str = Form(...), password: str = Form(...)):
    if login == ADMIN and password == ADMIN_PASSWORD:
        resp = RedirectResponse("/admin/panel", status_code=303)
        resp.set_cookie(ADMIN_COOKIE, "admin", httponly=True)
        return resp
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Неверный логин или пароль"})


@router.get('/admin/support', response_class=HTMLResponse)
async def support_page(request: Request, access_token: str = Cookie(None)):
    from infrastructure.repositiry.base_repository import AsyncSessionLocal
    from infrastructure.repositiry.user_repository import UserRepository
    from infrastructure.services.auth_service import AuthService
    from infrastructure.repositiry.db_models import ContactRequestORM
    from jwt.exceptions import DecodeError, ExpiredSignatureError
    if not access_token:
        return RedirectResponse('/admin')

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        auth_service = AuthService(secret_key=SECRET_KEY, user_repo=user_repo)

        try:
            # Проверяем токен
            token = auth_service.decode_token(access_token)
            nickname = token.get('sub')

            # Проверяем, что пользователь имеет права поддержки
            user = await user_repo.get_by_nickname(nickname)
            if not user or not user.is_support:
                return RedirectResponse('/admin')

            # Получаем все обращения из базы данных
            result = await session.execute(
                select(ContactRequestORM)
                .order_by(ContactRequestORM.created_at.desc())
            )
            contact_requests = result.scalars().all()

            # Передаем обращения в шаблон
            return templates.TemplateResponse(
                'admin_support.html',
                {
                    'request': request,
                    'contact_requests': contact_requests
                }
            )

        except (DecodeError, ExpiredSignatureError):
            return RedirectResponse('/admin')


@router.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, admin_session: str = Cookie(None)):
    if not admin_session or admin_session != "admin":
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import UserORM, OrderORM, MessageORM
        users = (await session.execute(select(UserORM))).scalars().all()
        orders = (await session.execute(select(OrderORM))).scalars().all()
        offers = (await session.execute(select(MessageORM).where(MessageORM.type == 'offer'))).scalars().all()
        return templates.TemplateResponse("admin_panel.html",
                                          {"request": request, "users": users, "orders": orders, "offers": offers})


@router.post("/admin/order/{order_id}/edit", response_class=HTMLResponse)
async def admin_edit_order(order_id: int, request: Request, admin_session: str = Cookie(None),
                           title: str = Form(...), description: str = Form(...), price: float = Form(...),
                           status: str = Form(...)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM
        from sqlalchemy import select
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return RedirectResponse("/admin/panel")
        order.name = title
        order.description = description
        order.price = price
        order.status = status
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/user/{user_id}/balance", response_class=HTMLResponse)
async def admin_edit_user_balance(user_id: int, request: Request, admin_session: str = Cookie(None),
                                  balance: float = Form(...)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import UserORM
        from sqlalchemy import select
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return RedirectResponse("/admin/panel")
        user.balance = balance
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/user/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user(user_id: int, request: Request, admin_session: str = Cookie(None),
                          name: str = Form(...), nickname: str = Form(...), email: str = Form(...),
                          balance: float = Form(...), customer_rating: float = Form(...)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import UserORM
        from sqlalchemy import select
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return RedirectResponse("/admin/panel")
        user.name = name
        user.nickname = nickname
        user.email = email
        user.balance = balance
        user.customer_rating = customer_rating
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/user/{user_id}/delete", response_class=HTMLResponse)
async def admin_delete_user(user_id: int, request: Request, admin_session: str = Cookie(None)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import UserORM
        from sqlalchemy import select
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await session.delete(user)
            await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/order/{order_id}/delete", response_class=HTMLResponse)
async def admin_delete_order(order_id: int, request: Request, admin_session: str = Cookie(None)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM
        from sqlalchemy import select
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            await session.delete(order)
            await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/offer/{offer_id}/edit", response_class=HTMLResponse)
async def admin_edit_offer(offer_id: int, request: Request, text: str = Form(...), order_id: int = Form(...),
                           admin_session: str = Cookie(None)):
    if not admin_session or admin_session != "admin":
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import MessageORM
        result = await session.execute(select(MessageORM).where(MessageORM.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            return JSONResponse({"error": "Offer not found"}, status_code=404)
        offer.text = text
        offer.order_id = order_id
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/offer/{offer_id}/delete", response_class=HTMLResponse)
async def admin_delete_offer(offer_id: int, request: Request, admin_session: str = Cookie(None)):
    if not admin_session or admin_session != "admin":
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import MessageORM
        result = await session.execute(select(MessageORM).where(MessageORM.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            return JSONResponse({"error": "Offer not found"}, status_code=404)
        await session.delete(offer)
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/order/{order_id}/change_executor", response_class=HTMLResponse)
async def admin_change_executor(order_id: int, request: Request, executor_id: int = Form(...),
                                admin_session: str = Cookie(None)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM
        from sqlalchemy import select
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        order.executor_id = executor_id
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.post("/admin/order/{order_id}/remove_executor", response_class=HTMLResponse)
async def admin_remove_executor(order_id: int, request: Request, admin_session: str = Cookie(None)):
    if not admin_session:
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.repositiry.db_models import OrderORM
        from sqlalchemy import select
        result = await session.execute(select(OrderORM).where(OrderORM.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if order.status == 'WORK':
            order.status = 'OPEN'
        order.executor_id = None
        await session.commit()
        return RedirectResponse("/admin/panel", status_code=303)


@router.get("/admin/commission", response_class=HTMLResponse)
async def admin_commission_page(request: Request, admin_session: str = Cookie(None)):
    if not admin_session or admin_session != "admin":
        return RedirectResponse("/admin")
    async with AsyncSessionLocal() as session:
        from infrastructure.services.order_service import OrderService
        order_service = OrderService(session)
        commission = await order_service.get_commission_settings(session) or {}
        return templates.TemplateResponse("admin_commission.html", {"request": request, "commission": commission})


@router.post("/admin/commission", response_class=HTMLResponse)
async def admin_commission_save(request: Request, admin_session: str = Cookie(None)):
    if not admin_session or admin_session != "admin":
        return RedirectResponse("/admin")
    form = await request.form()
    async with AsyncSessionLocal() as session:
        from infrastructure.services.order_service import OrderService
        order_service = OrderService(session)
        await order_service.set_commission_settings(
            session,
            commission_withdraw=float(form.get('commission_withdraw', 3.0)),
            commission_customer=float(form.get('commission_customer', 10.0)),
            commission_executor=float(form.get('commission_executor', 5.0)),
            commission_post_order=int(form.get('commission_post_order', 200)),
            commission_response_threshold=int(form.get('commission_response_threshold', 5000)),
            commission_response_percent=float(form.get('commission_response_percent', 1.0))
        )
        return RedirectResponse("/admin/commission", status_code=302)


@router.get("/api/search")
async def search_api(q: str):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from infrastructure.repositiry.db_models import OrderORM, UserORM, CategoryORM
        # Заказы
        orders = (await session.execute(
            select(OrderORM).where(
                (OrderORM.name.ilike(f"%{q}%")) | (OrderORM.description.ilike(f"%{q}%"))
            ).limit(10)
        )).scalars().all()
        # Пользователи
        users = (await session.execute(
            select(UserORM).where(
                (UserORM.name.ilike(f"%{q}%")) | (UserORM.nickname.ilike(f"%{q}%"))
            ).limit(10)
        )).scalars().all()
        # Категории
        categories = (await session.execute(
            select(CategoryORM).where(
                CategoryORM.name.ilike(f"%{q}%")
            ).limit(10)
        )).scalars().all()
        return {
            "orders": [{"id": o.id, "name": o.name, "type": "order"} for o in orders],
            "users": [{"id": u.nickname, "name": u.name, "nickname": u.nickname, "type": "user"} for u in users],
            "categories": [{"id": c.id, "name": c.name, "type": "category"} for c in categories]
        }


@router.get("/admin/support", response_class=HTMLResponse)
async def admin_support(request: Request, access_token: str = Cookie(None)):
    # Только для support или admin
    is_support = False
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        async with AsyncSessionLocal() as session:
            user = None
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user = result.scalar_one_or_none()
            if not user or (not user.is_support and nickname != ADMIN):
                return RedirectResponse("/login")
            is_support = user.is_support
            # Получаем все обращения
            reqs = await session.execute(select(ContactRequestORM).order_by(ContactRequestORM.created_at.desc()))
            contact_requests = reqs.scalars().all()
    except Exception:
        return RedirectResponse("/login")
    return templates.TemplateResponse("admin_support.html", {"request": request, "contact_requests": contact_requests,
                                                             "is_support": is_support})


@router.post("/admin/support/close/{req_id}")
async def close_contact_request(req_id: int, access_token: str = Cookie(None)):
    # Только для support или admin
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        async with AsyncSessionLocal() as session:
            user = None
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user = result.scalar_one_or_none()
            if not user or (not user.is_support and nickname != ADMIN):
                return RedirectResponse("/login")
            req = await session.get(ContactRequestORM, req_id)
            if req:
                req.status = "answered"
                await session.commit()
    except Exception:
        pass
    return RedirectResponse("/admin/support", status_code=303)


@router.post("/admin/support/broadcast")
async def support_broadcast(request: Request, message: str = Form(...), access_token: str = Cookie(None)):
    # Только для support или admin
    if not access_token:
        return RedirectResponse("/login")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        nickname = payload.get("sub")
        async with AsyncSessionLocal() as session:
            user = None
            result = await session.execute(select(UserORM).where(UserORM.nickname == nickname))
            user = result.scalar_one_or_none()
            if not user or (not user.is_support and nickname != ADMIN):
                return RedirectResponse("/login")
            # Получаем всех пользователей, кроме поддержки
            users = (await session.execute(select(UserORM).where(UserORM.is_support == False))).scalars().all()
            from infrastructure.repositiry.db_models import ChatORM, MessageORM
            from datetime import datetime
            # Для каждого пользователя создаём чат (если нет) и сообщение
            for u in users:
                chat = (await session.execute(select(ChatORM).where(
                    ((ChatORM.customer_id == user.id) & (ChatORM.executor_id == u.id)) |
                    ((ChatORM.customer_id == u.id) & (ChatORM.executor_id == user.id))
                ))).scalars().first()
                if not chat:
                    chat = ChatORM(customer_id=user.id, executor_id=u.id, created_at=datetime.utcnow())
                    session.add(chat)
                    await session.flush()
                msg = MessageORM(chat_id=chat.id, sender_id=user.id, text=message, type="support",
                                 created_at=datetime.utcnow())
                session.add(msg)
            await session.commit()
    except Exception:
        pass
    return RedirectResponse("/admin/support", status_code=303)
