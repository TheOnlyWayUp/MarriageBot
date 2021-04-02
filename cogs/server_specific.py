import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


MARRIAGEBOT_GOLD_INFORMATION = """
**MarriageBot Gold** is, put simply, the premium version of MarriageBot. It gives you a range of features that aren't present in the normal version of MarriageBot, which can help making your families even better than before.

**Server Specific Families**
> This allows you to keep families registered to your own guild. No more will you be trying to marry someone to find out they have a partner you've never met 4 servers away - all family members will be kept right on your server.
**5s Tree Command Cooldown**
> The tree command cooldown is reduced _massively_ to just 5s per command call, instead of the 60s that the regular MarriageBot has.
**"force" Commands**
> Users with a role named "MarriageBot Moderator" will be able to run commands like `forceadopt` and `forcemarry` in order to construct trees exactly how you want them.
**Configurable Max Family Members**
> Via the MarriageBot website, you're able to set the maximum number of members in a family to a number up to 2,000 people, putting it far above the amount offered normally.
**Configurable Max Children Amount**
> Stuck with only 5 children? Using the MarriageBot website, you're able to set the maximum number of children that a given role can have, allowing you to tier your users.
**Togglable Incest**
> You love your family? With Gold you're able to show them... a lot _more_ love.

MarriageBot Gold is a one-time purchase available per server on the MarriageBot website (<https://marriagebot.xyz/guilds>).
Please feel free to direct any questions to the team at `m!support`.
""".strip()


class ServerSpecific(utils.Cog):
    """
    Handles mostly marriagebot gold commands
    """

    @utils.Cog.listener()
    async def on_guild_join(self, guild:discord.Guild):
        """
        Looks for when the bot is added to a guild, leaving if it's not whitelisted.
        """

        if not self.bot.config['is_server_specific']:
            return
        async with self.bot.database() as db:
            data = await db("SELECT guild_id FROM guild_specific_families WHERE guild_id=$1", guild.id)
        if data:
            return
        self.logger.warn(f"Automatically left guild {guild.name} ({guild.id}) for non-subscription")
        await guild.leave()

    @utils.command(hidden=True)
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @localutils.checks.is_server_specific_bot_moderator()
    @localutils.checks.guild_is_server_specific()
    @commands.bot_has_permissions(send_messages=True)
    async def allowincest(self, ctx:utils.Context):
        """
        Toggles allowing incest on your guild.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, allow_incest) VALUES ($1, $2) ON CONFLICT (guild_id)
                DO UPDATE SET allow_incest=excluded.allow_incest""",
                ctx.guild.id, True,
            )
        self.bot.guild_settings[ctx.guild.id]['allow_incest'] = True
        await ctx.send("Incest is now **ALLOWED** on your guild.")

    @utils.command(hidden=True)
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @localutils.checks.is_server_specific_bot_moderator()
    @localutils.checks.guild_is_server_specific()
    @commands.bot_has_permissions(send_messages=True)
    async def disallowincest(self, ctx:utils.Context):
        """
        Toggles allowing incest on your guild.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, allow_incest) VALUES ($1, $2) ON CONFLICT (guild_id)
                DO UPDATE SET allow_incest=excluded.allow_incest""",
                ctx.guild.id, False,
            )
        self.bot.guild_settings[ctx.guild.id]['allow_incest'] = False
        await ctx.send("Incest is now **DISALLOWED** on your guild.")

    @utils.group()
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True)
    async def incest(self, ctx:utils.Context):
        """
        Toggles allowing incest on your guild.
        """

        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @incest.command(name="allow", aliases=['enable', 'on'])
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @localutils.checks.is_server_specific_bot_moderator()
    @localutils.checks.guild_is_server_specific()
    @commands.bot_has_permissions(send_messages=True)
    async def incest_allow(self, ctx:utils.Context):
        """
        Toggles allowing incest on your guild.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, allow_incest) VALUES ($1, $2) ON CONFLICT (guild_id)
                DO UPDATE SET allow_incest=excluded.allow_incest""",
                ctx.guild.id, True,
            )
        self.bot.guild_settings[ctx.guild.id]['allow_incest'] = True
        await ctx.send("Incest is now **ALLOWED** on your guild.")

    @incest.command(name="disallow", aliases=['disable', 'off'])
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @localutils.checks.is_server_specific_bot_moderator()
    @localutils.checks.guild_is_server_specific()
    @commands.bot_has_permissions(send_messages=True)
    async def incest_disallow(self, ctx:utils.Context):
        """
        Toggles allowing incest on your guild.
        """

        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, allow_incest) VALUES ($1, $2) ON CONFLICT (guild_id)
                DO UPDATE SET allow_incest=excluded.allow_incest""",
                ctx.guild.id, False,
            )
        self.bot.guild_settings[ctx.guild.id]['allow_incest'] = False
        await ctx.send("Incest is now **DISALLOWED** on your guild.")

    @utils.command(aliases=['ssf'])
    @utils.cooldown.no_raise_cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True)
    async def gold(self, ctx:utils.Context):
        """
        Gives you the information about server specific families and MarriageBot Gold.
        """

        try:
            await ctx.author.send(MARRIAGEBOT_GOLD_INFORMATION.strip())
            await ctx.send("Sent you a DM!")
        except discord.Forbidden:
            await ctx.send("I couldn't send you a DM :c")

    @utils.command()
    @localutils.checks.is_server_specific_bot_moderator()
    @commands.bot_has_permissions(send_messages=True)
    async def forcemarry(self, ctx:utils.Context, usera:utils.converters.UserID, userb:utils.converters.UserID=None):
        """
        Marries the two specified users.
        """

        # Correct params
        if userb is None:
            usera, userb = ctx.author.id, usera
        if usera == userb:
            return await ctx.send("You can't marry yourself.")

        # Get users
        family_guild_id = localutils.get_family_guild_id(ctx)
        usera_tree, userb_tree = localutils.FamilyTreeMember.get_multiple(usera, userb, guild_id=ctx.family_guild_id)

        # See if they have partners
        if usera_tree._partner is not None:
            user_name = await localutils.DiscordNameManager.fetch_name_by_id(self.bot, usera_tree.id)
            return await ctx.send(f"**{user_name}** already has a partner.", allowed_mentions=discord.AllowedMentions.none())
        if userb_tree._partner is not None:
            user_name = await localutils.DiscordNameManager.fetch_name_by_id(self.bot, userb_tree.id)
            return await ctx.send(f"**{user_name}** already has a partner.", allowed_mentions=discord.AllowedMentions.none())

        # Update database
        async with self.bot.database() as db:
            try:
                await db.start_transaction()
                await db(
                    "INSERT INTO marriages (user_id, partner_id, guild_id) VALUES ($1, $2, $3), ($2, $1, $3)",
                    usera_tree.id, userb_tree.id, family_guild_id,
                )
                await db.commit_transaction()
            except asyncpg.UniqueViolationError:
                return await ctx.send("I ran into an error saving your family data.")
        usera_name = await localutils.DiscordNameManager.fetch_name_by_id(self.bot, usera_tree.id)
        userb_name = await localutils.DiscordNameManager.fetch_name_by_id(self.bot, userb_tree.id)
        await ctx.send(f"Married **{usera_name}** and **{userb_name}**.", allowed_mentions=discord.AllowedMentions.none())

        # Update cache
        usera_tree._partner = userb
        userb_tree._partner = usera
        async with self.bot.redis() as re:
            await re.publish('TreeMemberUpdate', usera_tree.to_json())
            await re.publish('TreeMemberUpdate', userb_tree.to_json())

    @utils.command()
    @localutils.checks.is_server_specific_bot_moderator()
    @commands.bot_has_permissions(send_messages=True)
    async def forcedivorce(self, ctx:utils.Context, usera:utils.converters.UserID):
        """
        Divorces a user from their spouse.
        """

        # Get user
        family_guild_id = localutils.get_family_guild_id(ctx)
        usera_tree = localutils.FamilyTreeMember.get(usera, guild_id=family_guild_id)
        usera_name = await localutils.DiscordNameManager.fetch_name_by_id(self.bot, usera_tree.id)
        if not usera_tree.partner:
            return await ctx.send(f"**{usera_name}** isn't even married .-.", allowed_mentions=discord.AllowedMentions.none())

        # Update database
        async with self.bot.database() as db:
            await db(
                """DELETE FROM marriages WHERE (user_id=$1 OR partner_id=$1) AND guild_id=$2""",
                user, family_guild_id,
            )

        # Update cache
        usera_tree.partner._partner = None
        userb_tree = usera_tree.partner
        usera_tree._partner = None
        async with self.bot.redis() as re:
            await re.publish('TreeMemberUpdate', usera_tree.to_json())
            await re.publish('TreeMemberUpdate', userb_tree.to_json())
        await ctx.send("Consider it done.")

    @utils.command()
    @localutils.checks.is_server_specific_bot_moderator()
    @commands.bot_has_permissions(send_messages=True)
    async def forceadopt(self, ctx:utils.Context, parent:utils.converters.UserID, child:utils.converters.UserID=None):
        """
        Adds the child to the specified parent.
        """

        # Correct params
        if child is None:
            parent, child = ctx.author.id, parent

        # Check users
        them = localutils.FamilyTreeMember.get(child, ctx.family_guild_id)
        child_name = await self.bot.get_name(child)
        if them.parent:
            return await ctx.send(f"`{child_name!s}` already has a parent.")

        # Update database
        async with self.bot.database() as db:
            await db('INSERT INTO parents (parent_id, child_id, guild_id, timestamp) VALUES ($1, $2, $3, $4)', parent, child, ctx.family_guild_id, dt.utcnow())

        # Update cache
        me = localutils.FamilyTreeMember.get(parent, ctx.family_guild_id)
        me._children.append(child)
        them._parent = parent
        async with self.bot.redis() as re:
            await re.publish('TreeMemberUpdate', me.to_json())
            await re.publish('TreeMemberUpdate', them.to_json())
        await ctx.send(f"Added <@{child}> to <@{parent}>'s children list.")

    @utils.command(aliases=['forceeman'])
    @localutils.checks.is_server_specific_bot_moderator()
    @commands.bot_has_permissions(send_messages=True)
    async def forceemancipate(self, ctx:utils.Context, user:utils.converters.UserID):
        """
        Force emancipates a child.
        """

        # Run checks
        me = localutils.FamilyTreeMember.get(user, ctx.family_guild_id)
        if not me.parent:
            return await ctx.send(f"<@{me.id}> doesn't even have a parent .-.")

        # Update database
        async with self.bot.database() as db:
            await db('DELETE FROM parents WHERE child_id=$1 AND guild_id=$2', me.id, me._guild_id)

        # Update cache
        me.parent._children.remove(user)
        parent = me.parent
        me._parent = None
        async with self.bot.redis() as re:
            await re.publish('TreeMemberUpdate', me.to_json())
            await re.publish('TreeMemberUpdate', parent.to_json())
        await ctx.send("Consider it done.")


def setup(bot:utils.Bot):
    x = ServerSpecific(bot)
    bot.add_cog(x)
