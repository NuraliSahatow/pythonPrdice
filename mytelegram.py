def dice_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, player1_chat_id, player2_chat_id, player1_dice, player2_dice, status, Bet FROM rooms WHERE (player1_chat_id = ? OR player2_chat_id = ?) AND (status = ? OR status = ? OR status = ?)",
                           (user_id, user_id, ROOM_STATUS_BETTED, ROOM_STATUS_STARTED, ROOM_STATUS_OPEN))
            room = cursor.fetchone()

            if room:
                room_id, player1_chat_id, player2_chat_id, player1_dice, player2_dice, room_status, bet_amount = room
                if room_status == ROOM_STATUS_BETTED:
                    cursor.execute("UPDATE rooms SET status = 'open' WHERE id = ?", (room_id,))
                if room_status == ROOM_STATUS_STARTED:
                    print("Sending dice for player 1")
                    bot_dice = context.bot.send_dice(chat_id=player1_chat_id, emoji='🎲').dice.value
                    print(f"Player 1 dice value: {bot_dice}")
                    cursor.execute("UPDATE rooms SET player1_dice = ? WHERE id = ?", (bot_dice, room_id))
                    print("Sending dice for player 2")
                    bot_dice = context.bot.send_dice(chat_id=player2_chat_id, emoji='🎲').dice.value
                    print(f"Player 2 dice value: {bot_dice}")
                    cursor.execute("UPDATE rooms SET player2_dice = ? WHERE id = ?", (bot_dice, room_id))

                    conn.commit()

                    cursor.execute("SELECT player1_dice, player2_dice FROM rooms WHERE id = ?", (room_id,))
                    player1_dice, player2_dice = cursor.fetchone()

                    if player1_dice != 0 and player2_dice != 0:
                        if player1_dice > player2_dice:
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (bet_amount, player1_chat_id,))

                            cursor.execute("UPDATE users SET balance = balance - ? WHERE chat_id = ?", (bet_amount, player2_chat_id,))

                            winner_id = player1_chat_id
                        elif player1_dice < player2_dice:
                            cursor.execute("UPDATE users SET balance = balance - ? WHERE chat_id = ?", (bet_amount, player1_chat_id,))

                            cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (bet_amount, player2_chat_id,))

                            winner_id = player2_chat_id
                        else:
                            winner_id = None

                        # Deduct the bet amount from the room's Bet field
                        cursor.execute("UPDATE rooms SET Bet = Bet - ? WHERE id = ?", (bet_amount, room_id))

                        conn.commit()

                        context.bot.send_message(player1_chat_id, f"Вы бросили {player1_dice}, противник бросил {player2_dice}.")
                        context.bot.send_message(player2_chat_id, f"Вы бросили {player2_dice}, противник бросил {player1_dice}.")

                        if winner_id:
                            context.bot.send_message(winner_id, "Вы выиграли игру!")

                        cursor.execute("UPDATE rooms SET status = 'ended' WHERE id = ?", (room_id,))
                        conn.commit()

                    else:
                        context.bot.send_message(chat_id, "Ожидание броска противника...")

                elif room_status == ROOM_STATUS_ENDED:
                    context.bot.send_message(chat_id, "Ожидание начала игры...")
            else:
                context.bot.send_message(chat_id, "Ожидание начала игры...")

    except Exception as e:
        logger.error(f"Error in dice_handler: {str(e)}")
