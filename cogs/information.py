from random import choice
from os import remove
from re import compile
from io import BytesIO
from asyncio import sleep, create_subprocess_exec, wait_for, TimeoutError as AsyncTimeoutError
from datetime import datetime as dt

from discord import Member, File, User
from discord.ext.commands import command, Context, cooldown
from discord.ext.commands import CommandOnCooldown, MissingRequiredArgument, BadArgument, DisabledCommand
from discord.ext.commands.cooldowns import BucketType

from cogs.utils.custom_bot import CustomBot
from cogs.utils.checks.can_send_files import can_send_files, CantSendFiles
from cogs.utils.checks.is_voter import is_voter_predicate, is_voter, IsNotVoter
from cogs.utils.checks.is_donator import is_patreon, IsNotDonator, is_patreon_predicate
from cogs.utils.family_tree.family_tree_member import FamilyTreeMember
from cogs.utils.customised_tree_user import CustomisedTreeUser
from cogs.utils.custom_cog import Cog
from cogs.utils.checks.bot_is_ready import bot_is_ready, BotNotReady
from cogs.utils.converters import UserID


class Information(Cog):
    '''
    The information cog
    Handles all marriage/divorce/etc commands
    '''

    def __init__(self, bot:CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot
        self.substitution = compile(r'[^\x00-\x7F\x80-\xFF\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF]')


    async def cog_command_error(self, ctx:Context, error):
        '''
        Local error handler for the cog
        '''

        # Throw errors properly for me
        if ctx.original_author_id in self.bot.owners and not isinstance(error, (CommandOnCooldown, DisabledCommand, IsNotVoter, IsNotDonator, BotNotReady)):
            text = f'```py\n{error}```'
            await ctx.send(text)
            raise error

        # Can't send files
        if isinstance(error, CantSendFiles):
            try:
                await ctx.send("I'm not able to send files into this channel.")
            except Exception:
                await ctx.author.send("I'm unable to send messages into that channel.", ignore_error=True)
            return

        # Missing argument
        elif isinstance(error, MissingRequiredArgument):
            await ctx.send("You need to specify a person for this command to work properly.")
            return

        # Cooldown
        elif isinstance(error, CommandOnCooldown):
            # Bypass for owner
            if ctx.original_author_id in self.bot.owners:
                await ctx.reinvoke()
            # Possible bypass for voter
            elif ctx.command.name in ['tree', 'globaltree']:
                await self.tree_timeout_handler(ctx, error)
            else:
                await ctx.send(f"You can only use this command once every `{error.cooldown.per:.0f} seconds` per server. You may use this again in `{error.retry_after:.2f} seconds`.")
            return

        # Voter
        elif isinstance(error, IsNotVoter):
            # Bypass for owner
            if ctx.original_author_id in self.bot.owners:
                await ctx.reinvoke()
            else:
                await ctx.send(f"You need to vote on DBL (`{ctx.prefix}vote`) to be able to run this command.")
            return

        # Donator
        elif isinstance(error, IsNotDonator):
            # Bypass for owner
            if ctx.original_author_id in self.bot.owners:
                await ctx.reinvoke()
            else:
                await ctx.send(f"You need to be a Patreon subscriber (`{ctx.prefix}donate`) to be able to run this command.")
            return

        # Argument conversion error
        elif isinstance(error, BadArgument):
            argument_text = self.bot.bad_argument.search(str(error)).group(2)
            await ctx.send(f"User `{argument_text}` could not be found.")
            return

        # Disabled command
        elif isinstance(error, DisabledCommand):
            if ctx.original_author_id in self.bot.owners:
                await ctx.reinvoke()
            else:
                await ctx.send("This command has been temporarily disabled. Apologies for any inconvenience.")
            return

        # Bot ready
        elif isinstance(error, BotNotReady):
            await ctx.send("The bot isn't ready to start processing that command yet - please wait.")
            return


    async def tree_timeout_handler(self, ctx:Context, error):
        '''Handles errors for the tree commands'''

        is_patreon = await is_patreon_predicate(ctx.bot, ctx.author, 1)
        is_patreon_3 = await is_patreon_predicate(ctx.bot, ctx.author, 3)
        cooldown_time = min([
            error.cooldown.per if not self.bot.is_server_specific else 5,
            30 if is_voter_predicate(ctx) else error.cooldown.per,
            15 if is_patreon else error.cooldown.per,
            5 if is_patreon_3 else error.cooldown.per,
        ])

        if (error.cooldown.per - cooldown_time) > error.retry_after:
            ctx.command.reset_cooldown(ctx)
            await ctx.command.invoke(ctx)
            return
        else:
            cooldown_display = f"{error.cooldown.per:.0f} seconds"
            time_remaining = error.retry_after
            if cooldown_time < error.cooldown.per:
                cooldown_display = f"~~{error.cooldown.per:.0f} seconds~~ {cooldown_time:.0f} seconds"
                time_remaining = cooldown_time - (error.cooldown.per - error.retry_after)
            await ctx.send(f"You can only use this command once every {cooldown_display} (see `{ctx.clean_prefix}perks` for more information) per server. You may use this again in {time_remaining:.1f} seconds.")
            return


    @command(aliases=['spouse', 'husband', 'wife', 'marriage'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def partner(self, ctx:Context, user:UserID=None):
        '''
        Shows you the partner of a given user
        '''

        if not user:
            user = ctx.author.id

        # Get the user's info
        user_name = await self.bot.get_name(user)
        user_info = FamilyTreeMember.get(user, ctx.family_guild_id)
        if user_info._partner == None:
            await ctx.send(f"`{user_name}` is not currently married.")
            return

        partner_name = await self.bot.get_name(user_info._partner)
        await ctx.send(f"`{user_name}` is currently married to `{partner_name}` (`{user_info._partner}`).")


    @command(aliases=['child', 'kids'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def children(self, ctx:Context, user:UserID=None):
        '''
        Gives you a list of all of your children
        '''

        if user == None:
            user = ctx.author.id

        # Setup output variable
        output = ''

        # Get the user's info
        user_name = await self.bot.get_name(user)
        user_info = FamilyTreeMember.get(user, ctx.family_guild_id)
        if len(user_info._children) == 0:
            output += f"`{user_name}` has no children right now."
        else:
            output += f"`{user_name}` has `{len(user_info._children)}` child" + {False:"ren", True:""}.get(len(user_info._children)==1) + ": "
            out_names = []
            for i in user_info._children:
                name = await self.bot.get_name(i)
                out_names.append(f"`{name}` (`{i}`)")
            output += ', '.join(out_names) + '. '

        # Get their partner's info, if any
        if user_info._partner == None:
            await ctx.send(output)
            return
        user_info = user_info.partner
        user = await self.bot.get_name(user_info.id)
        if len(user_info._children) == 0:
            output += f"\n\nTheir partner, `{user}`, has no children right now."
        else:
            output += f"\n\nTheir partner, `{user}`, has `{len(user_info._children)}` child" + {False:"ren", True:""}.get(len(user_info._children)==1) + ": "
            out_names = []
            for i in user_info._children:
                name = await self.bot.get_name(i)
                out_names.append(f"`{name}` (`{i}`)")
            output += ', '.join(out_names) + '. '

        # Return all output
        await ctx.send(output)

    @command(aliases=['siblings'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def sibling(self, ctx:Context, user:User=None):
        '''
        Gives you a list of all of your siblings
        '''

        if user == None:
            user = ctx.author

        # Setup output variable
        output = ''

        # Get the parent's info
        user_info = FamilyTreeMember.get(user.id, ctx.family_guild_id)
        if user_info._parent == None:
            output += f"`{user!s}` has no parent right now."
            await ctx.send(output)
            return
        else:
            parent = user_info.parent
            if len(parent._children) <= 1:
                output += f"`{user!s}` has no siblings on their side of the family."
            else:
                output += f"`{user!s}` has `{len(parent._children) - 1}` sibling" + \
                {False:"s", True:""}.get(len(parent._children)==2) + \
                " from their parent's side: " + \
                ", ".join([f"`{self.bot.get_user(i)!s}` (`{i}`)" for i in parent._children if i != user.id]) + '. '

        parent = user_info.parent
        if parent._partner == None:
            await ctx.send(output)
            return

        other_parent = parent.partner
        if len(other_parent._children) == 0:
            output += f"\nThey also have no siblings from their parent's partner's side of the family."
            await ctx.send(output)
            return

        output += f"\nThey also have `{len(other_parent._children)}` sibling" + \
        {False:"s", True:""}.get(len(other_parent._children)==1) + \
        " from their parent's partner's side of the family: " + \
        ", ".join([f"`{self.bot.get_user(i)!s}` (`{i}`)" for i in other_parent._children]) + '. '

        # Return all output
        await ctx.send(output)


    @command(aliases=['parents'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def parent(self, ctx:Context, user:UserID=None):
        '''
        Tells you who someone's parent is
        '''

        if user == None:
            user = ctx.author.id

        user_info = FamilyTreeMember.get(user, ctx.family_guild_id)
        user_name = await self.bot.get_name(user)
        if user_info._parent == None:
            await ctx.send(f"`{user_name}` has no parent.")
            return
        name = await self.bot.get_name(user_info._parent)
        await ctx.send(f"`{user_name}`'s parent is `{name}` (`{user_info._parent}`).")


    @command(aliases=['relation'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def relationship(self, ctx:Context, user:User, other:User=None):
        '''
        Gets the relationship between the two specified users
        '''

        if user == ctx.author and other is None:
            await ctx.send(f"Unsurprisingly, you're pretty closely related to yourself.")
            return
        await ctx.channel.trigger_typing()

        if other == None:
            user, other = ctx.author, user
        user, other = FamilyTreeMember.get(user.id, ctx.family_guild_id), FamilyTreeMember.get(other.id, ctx.family_guild_id)
        async with ctx.channel.typing():
            relation = user.get_relation(other)

        username = await self.bot.get_name(user.id)
        othername = await self.bot.get_name(other.id)

        if relation == None:
            await ctx.send(f"`{username}` is not related to `{othername}`.")
            return
        await ctx.send(f"`{othername}` is `{username}`'s {relation}.")


    @command(aliases=['treesize','fs','ts'])
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def familysize(self, ctx:Context, user:User=None):
        '''
        Gives you the size of your family tree
        '''

        if user == None:
            user = ctx.author
        await ctx.channel.trigger_typing()

        user = FamilyTreeMember.get(user.id, ctx.family_guild_id)
        async with ctx.channel.typing():
            span = user.span(expand_upwards=True, add_parent=True)
        username = await self.bot.get_name(user.id)
        await ctx.send(f"There are `{len(span)}` people in `{username}`'s family tree.")


    @command(enabled=False)
    @can_send_files()
    @bot_is_ready()
    @cooldown(1, 5, BucketType.user)
    async def treefile(self, ctx:Context, root:Member=None):
        '''
        Gives you the full family tree of a user
        '''

        if root == None:
            root = ctx.author
        async with ctx.channel.typing():
            text = await FamilyTreeMember.get(root.id, ctx.family_guild_id).generate_gedcom_script(self.bot)
        file = BytesIO(text.encode())
        await ctx.send(file=File(file, filename=f'Tree of {root.id}.ged'))


    @command(aliases=['familytree', 't', 'fulltree', 'ft', 'gt'])
    @can_send_files()
    @bot_is_ready()
    @cooldown(1, 60, BucketType.guild)
    async def tree(self, ctx:Context, root:Member=None):
        '''
        Gets the family tree of a given user
        '''

        # if ctx.guild == None:
        #     await ctx.send("This command cannot be used in private messages. Please use the `fulltree` command in its place.")
        #     return

        try:
            return await self.treemaker(
                ctx=ctx,
                root=root,
                # all_guilds=False
                all_guilds=True,
            )
        except Exception as e:
            raise e


    @command(aliases=['st'])
    @can_send_files()
    @is_patreon(tier=2)
    @bot_is_ready()
    @cooldown(1, 60, BucketType.guild)
    async def stupidtree(self, ctx:Context, root:User=None):
        '''
        Gets the family tree of a given user
        '''

        try:
            return await self.treemaker(
                ctx=ctx,
                root=root,
                stupid_tree=True
            )
        except Exception as e:
            raise e


    async def treemaker(self, ctx:Context, root:User, all_guilds:bool=False, stupid_tree:bool=False):

        if root == None:
            root = ctx.author
        root_user = root

        # Get their family tree
        tree = FamilyTreeMember.get(root_user.id, ctx.family_guild_id)

        # Make sure they have one
        if tree.is_empty:
            await ctx.send(f"`{root_user!s}` has no family to put into a tree .-.")
            return
        # m = await ctx.send("Generating tree - this may take a few minutes...", embeddify=False)
        # await ctx.channel.trigger_typing()

        # Write their treemaker code to a file
        start_time = dt.now()
        async with self.bot.database() as db:
            ctu = await CustomisedTreeUser.get(ctx.author.id, db)
        async with ctx.channel.typing():
            if stupid_tree:
                dot_code = await tree.to_full_dot_script(self.bot, ctu)
            else:
                dot_code = await tree.to_dot_script(self.bot, None if all_guilds else ctx.guild, ctu)

        try:
            with open(f'{self.bot.config["tree_file_location"]}/{ctx.author.id}.gz', 'w', encoding='utf-8') as a:
                a.write(dot_code)
        except Exception as e:
            self.log_handler.error(f"Could not write to {self.bot.config['tree_file_location']}/{ctx.author.id}.gz")
            raise e

        # Convert to an image
        dot = await create_subprocess_exec(*[
            'dot',
            '-Tpng',
            f'{self.bot.config["tree_file_location"]}/{ctx.author.id}.gz',
            '-o',
            f'{self.bot.config["tree_file_location"]}/{ctx.author.id}.png',
            '-Gcharset=UTF-8',
            ], loop=self.bot.loop
        )
        await wait_for(dot.wait(), 10.0, loop=self.bot.loop)
        try:
            dot.kill()
        except ProcessLookupError:
            pass  # It already died
        except Exception as e:
            raise e

        # Get time taken
        end_time = dt.now()
        time_taken = (end_time - start_time).total_seconds()

        # Send file and delete cached
        try:
            file = File(fp=f'{self.bot.config["tree_file_location"]}/{ctx.author.id}.png')
            await ctx.send(f"[Click here](https://marriagebot.xyz/) to customise your tree. Generated in `{time_taken:.2f}` seconds from `{len(dot_code)}` bytes of DOT code.", file=file)
            await m.delete()
        except Exception as e:
            pass


def setup(bot:CustomBot):
    x = Information(bot)
    bot.add_cog(x)
